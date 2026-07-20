from app.core.observability import trace_graph_run


def test_trace_metadata_redacts_raw_prompt_document_and_csv_values() -> None:
    with trace_graph_run(
        "csv_analysis",
        {
            "route": "csv_analysis",
            "workspace_id": "workspace-123",
            "question": "secret customer question",
            "document_text": "private document text",
            "csv_rows": "VN,1250",
            "model_id": "gemma3:4b",
        },
    ) as trace:
        trace.set_status("ok")

    assert trace.metadata["route"] == "csv_analysis"
    assert trace.metadata["workspace_id_hash"] != "workspace-123"
    assert trace.metadata["model_id"] == "gemma3:4b"
    assert "question" not in trace.metadata
    assert "document_text" not in trace.metadata
    assert "csv_rows" not in trace.metadata
    assert trace.metadata["status"] == "ok"
    assert "latency_ms" in trace.metadata
