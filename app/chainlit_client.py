"""Small FastAPI client used exclusively by the Chainlit presentation layer."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterable, Iterator
from typing import Any

import httpx


class ApiError(RuntimeError):
    """A safe, user-displayable error returned by the local FastAPI service."""


class SSEEventParser:
    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, text: str) -> list[tuple[str, dict[str, Any]]]:
        self._buffer += text.replace("\r\n", "\n")
        events: list[tuple[str, dict[str, Any]]] = []
        while "\n\n" in self._buffer:
            frame, self._buffer = self._buffer.split("\n\n", 1)
            event_name = "message"
            data_lines: list[str] = []
            for line in frame.splitlines():
                if line.startswith("event:"):
                    event_name = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())
            if data_lines:
                events.append((event_name, json.loads("\n".join(data_lines))))
        return events


def parse_sse_events(chunks: Iterable[str]) -> Iterator[tuple[str, dict[str, Any]]]:
    parser = SSEEventParser()
    for chunk in chunks:
        yield from parser.feed(chunk)


def apply_chat_event(answer: str, event_name: str, payload: dict[str, Any]) -> str:
    """Apply an answer event, honoring the API's citation-validation replacement."""
    if event_name != "answer":
        return answer
    if payload.get("replace") is True:
        return str(payload.get("answer", ""))
    return answer + str(payload.get("delta", ""))


class LocalRagApi:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8100")).rstrip("/")

    @staticmethod
    def _error(response: httpx.Response) -> ApiError:
        try:
            detail = response.json().get("detail", response.text)
        except json.JSONDecodeError:
            detail = response.text
        return ApiError(str(detail) or f"FastAPI returned HTTP {response.status_code}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        **kwargs: Any,
    ) -> Any:
        headers = kwargs.pop("headers", {})
        if token:
            headers = {**headers, "Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
        if response.is_error:
            raise self._error(response)
        return response.json()

    async def login(self, email: str, password: str) -> str:
        payload = await self._request("POST", "/auth/login", json={"email": email, "password": password})
        return str(payload["access_token"])

    async def register(self, email: str, password: str) -> None:
        await self._request("POST", "/auth/register", json={"email": email, "password": password})

    async def list_workspaces(self, token: str) -> list[dict[str, Any]]:
        return await self._request("GET", "/workspaces", token=token)

    async def create_workspace(self, token: str, name: str) -> dict[str, Any]:
        return await self._request("POST", "/workspaces", token=token, json={"name": name})

    async def list_documents(self, token: str, workspace_id: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/workspaces/{workspace_id}/documents", token=token)

    async def upload_document(
        self, token: str, workspace_id: str, filename: str, content: bytes, mime_type: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/workspaces/{workspace_id}/documents",
            token=token,
            files={"file": (filename, content, mime_type)},
        )

    async def stream_chat(
        self,
        token: str,
        workspace_id: str,
        question: str,
        route: str,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        headers = {"Authorization": f"Bearer {token}"}
        parser = SSEEventParser()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"/workspaces/{workspace_id}/chat",
                headers=headers,
                json={"question": question, "route": route},
            ) as response:
                if response.is_error:
                    body = await response.aread()
                    raise ApiError(body.decode() or f"FastAPI returned HTTP {response.status_code}")
                async for chunk in response.aiter_text():
                    for event in parser.feed(chunk):
                        yield event
