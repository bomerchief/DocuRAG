from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    app_env: str
    database_url: str
    vector_db_path: str
    embedding_model: str
    llm_provider: str          # ollama | gemini | openai
    llm_model: str             # used by ollama and openai
    ollama_base_url: str
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    # RAG
    top_k: int
    chunk_size: int
    chunk_overlap: int
    similarity_threshold: float
    temperature: float
    prompt_version: str
    max_file_size_mb: int
    log_level: str = "INFO"
    openai_api_key: Optional[str] = None
    max_question_length: int = 2000
    rate_limit_per_minute: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
