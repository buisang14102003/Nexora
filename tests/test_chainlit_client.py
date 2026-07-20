from __future__ import annotations

from app.chainlit_client import apply_chat_event, parse_sse_events


def test_parse_sse_events_reads_answer_and_citations() -> None:
    events = list(
        parse_sse_events(
            [
                'event: answer\ndata: {"delta":"Draft answer"}\n\n',
                'event: citations\ndata: {"citations":[{"source_name":"policy.pdf","page_number":2}]}\n\n',
            ]
        )
    )

    assert events == [
        ("answer", {"delta": "Draft answer"}),
        (
            "citations",
            {"citations": [{"source_name": "policy.pdf", "page_number": 2}]},
        ),
    ]


def test_replace_answer_event_discards_unsupported_streamed_text() -> None:
    answer = "An unsupported draft"

    answer = apply_chat_event(answer, "answer", {"delta": " that must disappear"})
    answer = apply_chat_event(
        answer,
        "answer",
        {
            "answer": "I could not find that information in this workspace's documents.",
            "replace": True,
        },
    )

    assert answer == "I could not find that information in this workspace's documents."
