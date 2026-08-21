import datetime
import pytest
from qdrant_client import AsyncQdrantClient

from app.domain.rag.embeddings import MockEmbeddingProvider
from app.domain.rag.engine import RAGSubsystem
from app.domain.rag.models import Document, DocumentMetadata, RetrievalRequest


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider(dimension=384)


@pytest.fixture
async def qdrant_client() -> AsyncQdrantClient:
    # Use in-memory Qdrant instance for lightning fast, dependency-free testing
    client = AsyncQdrantClient(location=":memory:")
    yield client
    await client.close()


@pytest.fixture
def rag_subsystem(
    qdrant_client: AsyncQdrantClient,
    mock_embedding_provider: MockEmbeddingProvider,
) -> RAGSubsystem:
    return RAGSubsystem(
        client=qdrant_client,
        collection_name="eval_astrology_base",
        embedding_provider=mock_embedding_provider,
        chunk_size=100,
        chunk_overlap=10,
    )


@pytest.fixture
def evaluation_fixtures() -> list[Document]:
    """Retrieval evaluation fixtures representing Western, Vedic, and Numerology systems."""
    doc_western = Document(
        content=(
            "In Western astrology, the 10th house is called Midheaven. When the "
            "Sun is in the 10th house, it strongly signifies career progression, "
            "authority, and public visibility. The Placidus system is often used "
            "to compute these house cusps."
        ),
        metadata=DocumentMetadata(
            system="Western",
            methodology="Placidus",
            topic="Sun in 10th House",
            planet="Sun",
            house="10",
            domain="career",
            source="Western Astrology Manual",
            authority="Alan Leo",
            publication_date="2025-01-01",
        ),
    )

    doc_vedic = Document(
        content=(
            "In Vedic Jyotish astrology, the 10th house is the Karma Bhava. When "
            "Surya (the Sun) is placed in the Karma Bhava, it yields strong Digbala "
            "or directional strength. Vedic calculations often employ the Lahiri ayanamsa."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="Surya in 10th Bhava",
            planet="Surya",
            house="10",
            domain="career",
            source="Brihat Parashara Hora Shastra",
            authority="Sage Parashara",
            publication_date="2020-05-15",
        ),
    )

    doc_numerology = Document(
        content=(
            "In Numerology, the Personal Year 8 cycle represents a period of "
            "material acquisition, executive decision-making, and financial responsibility. "
            "It is governed by Saturn's vibrational energy."
        ),
        metadata=DocumentMetadata(
            system="Numerology",
            methodology="Chaldean",
            topic="Personal Year 8",
            domain="finance",
            source="Numerology Workbook",
            authority="Juno Jordan",
            publication_date="2026-02-10",
        ),
    )

    return [doc_western, doc_vedic, doc_numerology]


@pytest.mark.asyncio
async def test_rag_ingestion_and_chunking(
    rag_subsystem: RAGSubsystem, evaluation_fixtures: list[Document]
) -> None:
    # Ingest document
    doc = evaluation_fixtures[0]
    point_ids = await rag_subsystem.ingest_document(doc)

    # Chunks are expected since content length (~170 chars) exceeds chunk_size (100)
    assert len(point_ids) > 1

    # Verify points exist in Qdrant
    res = await rag_subsystem.client.count(rag_subsystem.collection_name)
    assert res.count == len(point_ids)


@pytest.mark.asyncio
async def test_rag_routing_and_isolation(
    rag_subsystem: RAGSubsystem, evaluation_fixtures: list[Document]
) -> None:
    # Ingest all fixtures
    await rag_subsystem.ingest_documents(evaluation_fixtures)

    # Query 1: Western focus (contain 'Placidus', 'Midheaven')
    req_west = RetrievalRequest(
        query="What does Midheaven and Placidus mean for my career?",
        limit=5,
    )
    results_west = await rag_subsystem.retrieve(req_west)
    assert len(results_west) > 0
    # Every returned result must belong to the 'Western' system to prevent cross-system mixing
    for r in results_west:
        assert r.system == "Western"
        assert "Surya" not in r.content

    # Query 2: Vedic focus (contains 'Karma Bhava' and 'Surya')
    req_vedic = RetrievalRequest(
        query="Explain Surya's placement in the Karma Bhava",
        limit=5,
    )
    results_vedic = await rag_subsystem.retrieve(req_vedic)
    assert len(results_vedic) > 0
    for r in results_vedic:
        assert r.system == "Vedic"
        assert "Placidus" not in r.content

    # Query 3: Numerology focus (contains 'Personal Year 8')
    req_num = RetrievalRequest(
        query="How does Personal Year 8 affect my finances?",
        limit=5,
    )
    results_num = await rag_subsystem.retrieve(req_num)
    assert len(results_num) > 0
    for r in results_num:
        assert r.system == "Numerology"
        assert "Karma" not in r.content


@pytest.mark.asyncio
async def test_rag_metadata_filtering(
    rag_subsystem: RAGSubsystem, evaluation_fixtures: list[Document]
) -> None:
    await rag_subsystem.ingest_documents(evaluation_fixtures)

    # Explicit filter for Vedic domain
    req = RetrievalRequest(
        query="Tell me about the 10th house",
        system="Vedic",
        limit=5,
    )
    results = await rag_subsystem.retrieve(req)
    assert len(results) > 0
    for r in results:
        assert r.system == "Vedic"


@pytest.mark.asyncio
async def test_rag_versioning_and_provenance(
    rag_subsystem: RAGSubsystem, evaluation_fixtures: list[Document]
) -> None:
    doc = evaluation_fixtures[0]  # Alan Leo's Placidus doc
    await rag_subsystem.ingest_document(doc)

    # Update document version
    updated_doc = Document(
        content=(
            "In Western astrology, the 10th house is called Midheaven. "
            "This updated version now includes more information about solar aspects."
        ),
        metadata=DocumentMetadata(
            system="Western",
            methodology="Placidus",
            topic="Sun in 10th House",
            planet="Sun",
            house="10",
            domain="career",
            source="Western Astrology Manual",
            authority="Alan Leo",
            version="2.0.0",  # Increment version
            publication_date="2026-08-19",
        ),
    )

    # Ingesting the updated version of the same source
    # First clear old version to maintain clean provenance
    await rag_subsystem.delete_document_by_source(updated_doc.metadata.source)
    await rag_subsystem.ingest_document(updated_doc)

    # Verify provenance values
    req = RetrievalRequest(query="Explain the Midheaven", limit=1)
    results = await rag_subsystem.retrieve(req)
    assert len(results) > 0
    res = results[0]
    assert res.version == "2.0.0"
    assert res.authority == "Alan Leo"
    assert res.publication_date == "2026-08-19"
    assert "updated version" in res.content


@pytest.mark.asyncio
async def test_rag_hybrid_reranking(
    rag_subsystem: RAGSubsystem, evaluation_fixtures: list[Document]
) -> None:
    await rag_subsystem.ingest_documents(evaluation_fixtures)

    req = RetrievalRequest(
        query="Surya in the Karma Bhava",
        rerank=True,
        limit=5,
    )
    results = await rag_subsystem.retrieve(req)
    assert len(results) > 0

    # The top result should be Vedic Surya and must have rerank_score populated
    top_res = results[0]
    assert top_res.system == "Vedic"
    assert top_res.rerank_score is not None
    assert top_res.rerank_score > 0.0
