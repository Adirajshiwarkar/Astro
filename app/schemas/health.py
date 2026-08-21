from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str = Field(
        ..., description="Status of the component ('healthy' or 'unhealthy')"
    )
    details: str | None = Field(
        None, description="Optional details or latency/version info"
    )


class HealthResponse(BaseModel):
    status: str = Field(
        ..., description="Overall app status ('healthy' or 'unhealthy')"
    )
    version: str = Field(..., description="Application version")
    database: ComponentHealth
    qdrant: ComponentHealth
