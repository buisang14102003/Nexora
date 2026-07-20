from uuid import UUID

from app.services.csv_analysis import CsvEvidence, CsvResult


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _workspace(client, token: str) -> str:
    response = client.post("/workspaces", headers=_headers(token), json={"name": "Finance"})
    assert response.status_code == 201
    return response.json()["id"]


def test_member_can_run_validated_csv_operation_for_own_workspace(
    client, register_and_login, monkeypatch
) -> None:
    from app.api.routers import chat

    token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, token)
    document_id = UUID("00000000-0000-0000-0000-000000000020")
    expected = CsvResult(
        values=[{"sum_amount": 1250.0}],
        evidence=CsvEvidence(
            source_name="sales.csv",
            columns=["country", "amount"],
            filters=[{"column": "country", "operator": "eq", "value": "VN"}],
            row_range="2-4",
            row_count=2,
        ),
    )
    captured = {}

    def run(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(chat, "run_csv_operation", run)

    response = client.post(
        f"/workspaces/{workspace_id}/csv-analysis",
        headers=_headers(token),
        json={
            "document_id": str(document_id),
            "operation": {
                "filters": [{"column": "country", "operator": "eq", "value": "VN"}],
                "group_by": [],
                "aggregations": [{"column": "amount", "function": "sum"}],
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["evidence"]["columns"] == ["country", "amount"]
    assert captured["workspace_id"] == UUID(workspace_id)
    assert captured["document_id"] == document_id


def test_non_member_cannot_run_csv_operation_in_another_workspace(
    client, register_and_login, monkeypatch
) -> None:
    from app.api.routers import chat

    owner_token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, owner_token)
    other_token = register_and_login("other@example.test")
    monkeypatch.setattr(chat, "run_csv_operation", lambda **_: (_ for _ in ()).throw(AssertionError))

    response = client.post(
        f"/workspaces/{workspace_id}/csv-analysis",
        headers=_headers(other_token),
        json={"document_id": "00000000-0000-0000-0000-000000000020", "operation": {}},
    )

    assert response.status_code == 404
