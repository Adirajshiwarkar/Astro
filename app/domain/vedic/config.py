from pydantic import BaseModel, Field


class VedicEngineConfig(BaseModel):
    engine_version: str = "1.0.0"
    default_ayanamsa: str = "lahiri"
