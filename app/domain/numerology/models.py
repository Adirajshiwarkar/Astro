from pydantic import BaseModel, Field


class NumerologyCalculationResult(BaseModel):
    calculated_value: int = Field(
        ...,
        description="The final reduced single-digit or master number result",
    )
    methodology: str = Field(
        ..., description="The system and formula details used for calculation"
    )
    source_input: str = Field(
        ..., description="The original input data (e.g. name or birth date)"
    )
    calculation_steps: list[str] = Field(
        ..., description="Step-by-step breakdown of intermediate sums"
    )
    engine_version: str = Field(
        ..., description="Version of the numerology engine"
    )


class NumerologyProfile(BaseModel):
    life_path: NumerologyCalculationResult
    birthday_number: NumerologyCalculationResult
    destiny_expression: NumerologyCalculationResult
    soul_urge: NumerologyCalculationResult
    personality_number: NumerologyCalculationResult
    personal_year: NumerologyCalculationResult | None = None
    personal_month: NumerologyCalculationResult | None = None
    methodology: str = Field(
        default="Pythagorean Numerology System",
        description="Methodology used for profile calculations",
    )
    engine_version: str = Field(
        default="1.0.0",
        description="Engine version",
    )

