from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3.5:mini"

    chunk_size: int = 400
    chunk_overlap: int = 60
    top_k_results: int = 5

    books_dir: Path = Path("../book_data")
    chroma_dir: Path = Path("./data/chroma")

    frontend_origin: str = "http://localhost:5173"

    @property
    def books_path(self) -> Path:
        return self.books_dir.resolve()

    @property
    def chroma_path(self) -> Path:
        return self.chroma_dir.resolve()


settings = Settings()
