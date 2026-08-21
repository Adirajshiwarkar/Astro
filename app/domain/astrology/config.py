from pydantic import BaseModel, Field


class AstrologyEngineConfig(BaseModel):
    engine_version: str = "1.0.0"
    orbs: dict[str, float] = Field(
        default_factory=lambda: {
            "conjunction": 8.0,
            "sextile": 6.0,
            "square": 8.0,
            "trine": 8.0,
            "opposition": 8.0,
        }
    )
