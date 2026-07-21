from app.db.models import ChatMessage, ChatSession


def test_chat_models_store_session_messages_and_citations() -> None:
    assert ChatSession.__tablename__ == "chat_sessions"
    assert ChatMessage.__tablename__ == "chat_messages"
    assert "session_id" in ChatMessage.__table__.columns
    assert "citations" in ChatMessage.__table__.columns
