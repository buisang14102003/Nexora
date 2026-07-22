import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_rejects_blank_database_url() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        Settings(database_url="", jwt_secret="test-secret")


def test_settings_rejects_chunk_size_above_embedding_limit() -> None:
    with pytest.raises(ValidationError, match="chunk_size_tokens"):
        Settings(
            database_url="sqlite://",
            jwt_secret="test-secret",
            chunk_size_tokens=33,
            embedding_max_tokens=32,
        )


def test_settings_default_to_local_ollama_embeddings() -> None:
    settings = Settings(database_url="sqlite://", jwt_secret="test-secret")

    assert settings.embedding_model == "qwen3-embedding:0.6b"
    assert settings.embedding_base_url == "http://host.docker.internal:11434"
