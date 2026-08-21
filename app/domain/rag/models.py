from typing import Optional
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    system: str = Field(
        ...,
        description="Astrological/Numerological system: e.g. 'Western', 'Vedic', 'Numerology'",
    )
    methodology: Optional[str] = Field(
        None, description="Astrological method/rules, e.g. 'Parashari', 'Placidus'"
    )
    topic: Optional[str] = Field(
        None, description="Topic of the document: e.g. 'planetary strength', 'dasha'"
    )
    planet: Optional[str] = Field(None, description="Associated planet/graha, if any")
    sign: Optional[str] = Field(None, description="Associated sign/rashi, if any")
    house: Optional[str] = Field(None, description="Associated house/bhava, if any")
    domain: Optional[str] = Field(
        None, description="Life domain: e.g. 'career', 'finance', 'relationship'"
    )
    source: str = Field(
        ..., description="Source of the document text / book / authority name"
    )
    version: str = Field("1.0.0", description="Version of the document representation")
    authority: Optional[str] = Field(
        None, description="Astrological authority/author name"
    )
    publication_date: Optional[str] = Field(
        None, description="Publication or update date"
    )


class Document(BaseModel):
    content: str = Field(..., description="Raw text content of the document")
    metadata: DocumentMetadata = Field(..., description="Document metadata")


class RetrievalRequest(BaseModel):
    query: str = Field(..., description="Semantic search query")
    system: Optional[str] = Field(
        None, description="System filter (e.g. 'Western', 'Vedic', 'Numerology')"
    )
    methodology: Optional[str] = Field(None, description="Methodology filter")
    domain: Optional[str] = Field(None, description="Domain filter")
    planet: Optional[str] = Field(None, description="Planet filter")
    sign: Optional[str] = Field(None, description="Sign filter")
    house: Optional[str] = Field(None, description="House filter")
    limit: int = Field(5, ge=1, le=50, description="Max number of results to return")
    rerank: bool = Field(False, description="Enable hybrid lexical reranking")


class RetrievalResult(BaseModel):
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., description="Similarity score")
    system: str = Field(..., description="Source system")
    methodology: Optional[str] = None
    topic: Optional[str] = None
    planet: Optional[str] = None
    sign: Optional[str] = None
    house: Optional[str] = None
    domain: Optional[str] = None
    source: str = Field(..., description="Source document or origin")
    version: str = Field(..., description="Document version")
    authority: Optional[str] = None
    publication_date: Optional[str] = None
    rerank_score: Optional[float] = None
