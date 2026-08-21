import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "AstroAPI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkeychangemeinproduction"

    CORS_ORIGINS: list[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                if v.startswith("[") and v.endswith("]"):
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                return [i.strip() for i in v.split(",") if i.strip()]
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []

    # MongoDB Settings
    MONGO_URI: str = "mongodb://localhost:27017/"
    MONGO_DB: str = "astroDB"

    # Qdrant Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None
    QDRANT_USE_SSL: bool = False

    # OpenAI / LLM Settings
    OPENAI_KEY: str | None = None

    # Logging Settings
    LOG_LEVEL: str = "INFO"


settings = Settings()
