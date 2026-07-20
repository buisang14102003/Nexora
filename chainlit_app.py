"""Chainlit UI for the local workspace RAG API.

This module deliberately has no database, object store, vector store, or model imports.
"""

from __future__ import annotations

from typing import Any

import chainlit as cl

from app.chainlit_client import ApiError, LocalRagApi, apply_chat_event


_SUPPORTED_FILES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/csv": [".csv"],
    "image/*": [".png", ".jpg", ".jpeg"],
}


def _api() -> LocalRagApi:
    return LocalRagApi()


def _session(name: str, default: Any = None) -> Any:
    return cl.user_session.get(name, default)


async def _ask_text(content: str) -> str | None:
    response = await cl.AskUserMessage(content=content, timeout=300).send()
    if response is None:
        return None
    return str(response["output"]).strip()


async def _authenticate() -> bool:
    email = await _ask_text("Email đăng nhập:")
    password = await _ask_text("Mật khẩu:")
    if not email or not password:
        await cl.Message(content="Đã hết thời gian đăng nhập. Hãy tải lại trang để thử lại.").send()
        return False

    api = _api()
    try:
        token = await api.login(email, password)
    except ApiError as exc:
        create = await _ask_text(
            f"Không đăng nhập được ({exc}). Gõ CREATE để tạo tài khoản mới bằng email này, hoặc bỏ trống để dừng:"
        )
        if create != "CREATE":
            return False
        try:
            await api.register(email, password)
            token = await api.login(email, password)
        except ApiError as register_error:
            await cl.Message(content=f"Không thể tạo tài khoản: {register_error}").send()
            return False

    cl.user_session.set("token", token)
    cl.user_session.set("email", email)
    return True


async def _show_workspace_actions() -> None:
    token = _session("token")
    if not token:
        return
    try:
        workspaces = await _api().list_workspaces(token)
    except ApiError as exc:
        await cl.Message(content=f"Không tải được workspace: {exc}").send()
        return

    actions = [
        cl.Action(name="create_workspace", label="Tạo workspace", payload={}),
        cl.Action(name="show_documents", label="Xem tài liệu", payload={}),
        cl.Action(name="set_summary", label="Chế độ tóm tắt", payload={}),
        cl.Action(name="set_rag", label="Hỏi tài liệu", payload={}),
    ]
    for workspace in workspaces:
        actions.insert(
            0,
            cl.Action(
                name="select_workspace",
                label=f"Chọn: {workspace['name']}",
                payload={"id": str(workspace["id"]), "name": workspace["name"]},
            ),
        )
    current = _session("workspace_name")
    prefix = f"Workspace hiện tại: **{current}**. " if current else "Chưa chọn workspace. "
    await cl.Message(content=prefix + "Chọn workspace hoặc tạo workspace mới.", actions=actions).send()


async def _show_documents() -> None:
    token, workspace_id = _session("token"), _session("workspace_id")
    if not token or not workspace_id:
        await cl.Message(content="Hãy chọn workspace trước.").send()
        return
    try:
        documents = await _api().list_documents(token, workspace_id)
    except ApiError as exc:
        await cl.Message(content=f"Không tải được danh sách tài liệu: {exc}").send()
        return
    if not documents:
        await cl.Message(content="Workspace chưa có tài liệu. Dùng biểu tượng kẹp giấy để tải PDF, DOCX, CSV hoặc ảnh.").send()
        return
    rows = "\n".join(f"- `{item['original_filename']}` — **{item['status']}**" for item in documents)
    await cl.Message(content=f"Tài liệu trong **{_session('workspace_name')}**:\n{rows}").send()


async def _upload_elements(elements: list[Any]) -> None:
    token, workspace_id = _session("token"), _session("workspace_id")
    if not workspace_id or not token:
        await cl.Message(content="Hãy chọn workspace trước khi tải file.").send()
        return
    api = _api()
    for element in elements:
        path = getattr(element, "path", None)
        name = getattr(element, "name", None)
        mime = getattr(element, "mime", None) or "application/octet-stream"
        if not path or not name:
            continue
        try:
            with open(path, "rb") as uploaded:
                document = await api.upload_document(token, workspace_id, name, uploaded.read(), mime)
            await cl.Message(content=f"Đã đưa `{document['original_filename']}` vào hàng đợi — trạng thái: **{document['status']}**.").send()
        except (OSError, ApiError) as exc:
            await cl.Message(content=f"Không thể tải `{name}`: {exc}").send()


def _citation_lines(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return ""
    lines: list[str] = []
    for citation in citations:
        location = citation.get("page_number")
        if location is not None:
            location = f"trang {location}"
        elif citation.get("row_range"):
            location = f"CSV {citation['row_range']}"
        else:
            location = "vị trí không xác định"
        lines.append(f"- {citation.get('source_name', 'Tài liệu')} — {location}")
    return "\n\nNguồn:\n" + "\n".join(lines)


@cl.on_chat_start
async def start() -> None:
    cl.user_session.set("route", "document_rag")
    if await _authenticate():
        await cl.Message(
            content="Đăng nhập thành công. Chọn workspace, sau đó tải tài liệu bằng biểu tượng kẹp giấy hoặc gửi câu hỏi."
        ).send()
        await _show_workspace_actions()


@cl.action_callback("select_workspace")
async def select_workspace(action: cl.Action) -> None:
    cl.user_session.set("workspace_id", action.payload["id"])
    cl.user_session.set("workspace_name", action.payload["name"])
    await action.remove()
    await _show_documents()


@cl.action_callback("create_workspace")
async def create_workspace(_: cl.Action) -> None:
    name = await _ask_text("Tên workspace mới:")
    if not name:
        return
    try:
        workspace = await _api().create_workspace(_session("token"), name)
    except ApiError as exc:
        await cl.Message(content=f"Không thể tạo workspace: {exc}").send()
        return
    cl.user_session.set("workspace_id", str(workspace["id"]))
    cl.user_session.set("workspace_name", workspace["name"])
    await cl.Message(content=f"Đã tạo và chọn workspace **{workspace['name']}**.").send()


@cl.action_callback("show_documents")
async def show_documents(_: cl.Action) -> None:
    await _show_documents()


@cl.action_callback("set_summary")
async def set_summary(_: cl.Action) -> None:
    cl.user_session.set("route", "summary")
    await cl.Message(content="Chế độ tóm tắt đã bật. Gửi yêu cầu tóm tắt tài liệu trong workspace.").send()


@cl.action_callback("set_rag")
async def set_rag(_: cl.Action) -> None:
    cl.user_session.set("route", "document_rag")
    await cl.Message(content="Chế độ hỏi tài liệu đã bật.").send()


@cl.on_message
async def chat(message: cl.Message) -> None:
    if message.elements:
        await _upload_elements(message.elements)
    question = message.content.strip()
    if not question:
        return
    if question == "/workspace":
        await _show_workspace_actions()
        return
    if question == "/documents":
        await _show_documents()
        return

    token, workspace_id = _session("token"), _session("workspace_id")
    if not token or not workspace_id:
        await cl.Message(content="Hãy chọn workspace trước bằng `/workspace`.").send()
        return

    answer = ""
    citations: list[dict[str, Any]] = []
    response = cl.Message(content="")
    try:
        async for event_name, payload in _api().stream_chat(
            token, workspace_id, question, _session("route", "document_rag")
        ):
            if event_name == "answer":
                previous = answer
                answer = apply_chat_event(answer, event_name, payload)
                if payload.get("replace") is True:
                    response.content = answer
                    await response.update()
                elif answer != previous:
                    await response.stream_token(answer[len(previous) :])
            elif event_name == "citations":
                citations = list(payload.get("citations", []))
    except ApiError as exc:
        await cl.Message(content=f"Không thể xử lý câu hỏi: {exc}").send()
        return

    response.content = (answer or "Không nhận được câu trả lời.") + _citation_lines(citations)
    await response.send()
