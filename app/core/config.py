from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "rag"
    minio_secret_key: str = ""
    minio_bucket: str = "documents"
    minio_secure: bool = False
    upload_max_bytes: int = 25 * 1024 * 1024
    qdrant_url: str = "http://qdrant:6333"
    ollama_base_url: str = "http://host.docker.internal:11434"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    chat_model: str = "gemma3:4b"
    embedding_model: str = "qwen3-embedding:0.6b"

    @field_validator("database_url")
    @classmethod
    def database_url_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must not be blank")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
