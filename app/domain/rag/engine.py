from typing import Optional, Sequence
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.domain.rag.embeddings import EmbeddingProvider, MockEmbeddingProvider
from app.domain.rag.models import Document, RetrievalRequest, RetrievalResult
from app.domain.rag.pipeline import DocumentIngestionPipeline
from app.domain.rag.retrieval import KnowledgeRetrievalEngine


class RAGSubsystem:
    """RAGSubsystem coordinates the ingestion pipeline and the knowledge retrieval engine."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str = "astrology_knowledge_base",
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()

        self.pipeline = DocumentIngestionPipeline(
            embedding_provider=self.embedding_provider,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        self.retrieval_engine = KnowledgeRetrievalEngine(
            embedding_provider=self.embedding_provider
        )

    async def ingest_document(self, document: Document) -> list[str]:
        """Ingest a single document: parse, clean, chunk, embed, and index it in Qdrant."""
        return await self.pipeline.ingest_document(
            client=self.client,
            collection_name=self.collection_name,
            document=document,
        )

    async def ingest_documents(self, documents: Sequence[Document]) -> list[str]:
        """Ingest a collection of documents."""
        all_point_ids = []
        for doc in documents:
            point_ids = await self.ingest_document(doc)
            all_point_ids.extend(point_ids)
        return all_point_ids

    async def retrieve(self, request: RetrievalRequest) -> list[RetrievalResult]:
        """Retrieve relevant context for a given query and filtering requirements."""
        return await self.retrieval_engine.retrieve(
            client=self.client,
            collection_name=self.collection_name,
            request=request,
        )

    async def delete_document_by_source(self, source: str) -> None:
        """Delete all chunks belonging to a specific source (for provenance & version updates)."""
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            ),
        )

    async def clear_knowledge_base(self) -> None:
        """Delete the current knowledge base collection."""
        try:
            await self.client.delete_collection(self.collection_name)
        except Exception:
            pass
