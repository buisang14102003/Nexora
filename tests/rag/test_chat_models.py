from app.db.models import ChatCitation, ChatMessage


def test_chat_models_store_answer_and_citation_evidence() -> None:
    assert ChatMessage.__tablename__ == "chat_messages"
    assert ChatCitation.__tablename__ == "chat_citations"
