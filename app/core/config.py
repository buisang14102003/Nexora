from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
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
    qdrant_collection: str = "document_chunks"
    ollama_base_url: str = "http://host.docker.internal:11434"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    chat_model: str = "gemma3:4b"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_tokenizer: str = "local-byte"
    embedding_max_tokens: int = 32_768
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 50
    ocr_languages: str = "eng+vie"
    ocr_dpi: int = 300
    worker_poll_seconds: float = 2.0
    langfuse_host: str = "http://langfuse-web:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    @field_validator("database_url")
    @classmethod
    def database_url_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must not be blank")
        return value

    @model_validator(mode="after")
    def ingestion_settings_are_valid(self) -> Self:
        if self.embedding_max_tokens <= 0:
            raise ValueError("embedding_max_tokens must be positive")
        if self.chunk_size_tokens <= 0:
            raise ValueError("chunk_size_tokens must be positive")
        if self.chunk_size_tokens > self.embedding_max_tokens:
            raise ValueError(
                "chunk_size_tokens must not exceed embedding_max_tokens"
            )
        if self.chunk_overlap_tokens < 0:
            raise ValueError("chunk_overlap_tokens must be non-negative")
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError(
                "chunk_overlap_tokens must be smaller than chunk_size_tokens"
            )
        if not self.embedding_tokenizer.strip():
            raise ValueError("embedding_tokenizer must not be blank")
        if not self.ocr_languages.strip():
            raise ValueError("ocr_languages must not be blank")
        if self.ocr_dpi <= 0:
            raise ValueError("ocr_dpi must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
