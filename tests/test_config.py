import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_rejects_blank_database_url() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        Settings(database_url="", jwt_secret="test-secret")
