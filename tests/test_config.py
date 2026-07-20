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
