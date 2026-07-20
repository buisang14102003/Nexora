from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    minio_endpoint: str = "minio:9000"
    qdrant_url: str = "http://qdrant:6333"
    ollama_base_url: str = "http://host.docker.internal:11434"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    chat_model: str = "gemma3:4b"
    embedding_model: str = "qwen3-embedding:0.6b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
