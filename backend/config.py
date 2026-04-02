"""Configuration management for the Research Paper Analyzer backend."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    app_name: str = "Research Paper Analyzer API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Data paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    upload_dir: Path = data_dir / "uploads"
    vector_dir: Path = data_dir / "vectors"
    db_dir: Path = data_dir / "db"

    # Database
    database_url: str = "sqlite:///./data/db/papers.db"

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_chunks_per_doc: int = 500

    # Retrieval
    top_k_results: int = 5
    similarity_threshold: float = 0.3

    # LLM / Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    llm_timeout: int = 120

    # File upload
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "txt"]

    # CORS
    allowed_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        """Create necessary directories after initialization."""
        for directory in [self.upload_dir, self.vector_dir, self.db_dir]:
            directory.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
