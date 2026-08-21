from typing import Any

from pydantic import BaseModel, Field


class VersionMetadata(BaseModel):
    astrology_engine_version: str = Field(
        default="1.0.0", description="Version of the calculation engine"
    )
    prediction_rules_version: str = Field(
        default="1.0.0", description="Version of the prediction rules"
    )
    knowledge_version: str = Field(
        default="1.0.0", description="Version of RAG knowledge database schema"
    )
    prompt_version: str = Field(
        default="1.0.0", description="Version of system prompt template"
    )


class ContextPackage(BaseModel):
    query: str = Field(..., description="The parsed user query")
    relevant_system: str | None = Field(
        None, description="Detected system context: Western, Vedic, Numerology"
    )
    relevant_domains: list[str] = Field(
        default_factory=list, description="Target domains detected from query"
    )
    chart: dict[str, Any] | None = Field(
        None, description="Trimmed astrological chart input"
    )
    western_factors: list[dict[str, Any]] | None = Field(
        None, description="Filtered Western factors"
    )
    vedic_factors: list[dict[str, Any]] | None = Field(
        None, description="Filtered Vedic factors"
    )
    numerology_factors: list[dict[str, Any]] | None = Field(
        None, description="Filtered Numerology factors"
    )
    signals: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevance filtered signals"
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevance filtered evidence trail items"
    )
    predictions: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevance filtered candidate predictions"
    )
    timeline: dict[str, Any] | None = Field(
        None, description="Trimmed timeline intervals"
    )
    scenarios: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevance filtered scenarios"
    )
    rag_results: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevance filtered RAG search results"
    )
    relevant_memory: list[dict[str, Any]] = Field(
        default_factory=list, description="Filtered user conversational memories"
    )
    chart_validation_results: dict[str, Any] | None = Field(
        None, description="Trimmed validation logs and warnings"
    )
    version_metadata: VersionMetadata = Field(
        default_factory=VersionMetadata,
        description="Version configurations across engines",
    )
