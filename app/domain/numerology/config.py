from enum import Enum
from pydantic import BaseModel, Field


class NumerologySystem(str, Enum):
    PYTHAGOREAN = "Pythagorean Numerology System"


class NumerologyConfig(BaseModel):
    engine_version: str = Field(
        default="1.0.0",
        description="Version of the numerology engine",
    )
    methodology: NumerologySystem = Field(
        default=NumerologySystem.PYTHAGOREAN,
        description="Active numerology system methodology",
    )
    preserve_master_numbers: bool = Field(
        default=True,
        description="Whether to preserve master numbers (11, 22, 33) without reducing to single digits",
    )
    master_numbers: tuple[int, ...] = Field(
        default=(11, 22, 33),
        description="Tuple of master numbers to preserve during reduction",
    )

