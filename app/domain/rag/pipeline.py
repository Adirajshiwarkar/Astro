import datetime
import re
import uuid
from typing import Sequence
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.domain.rag.embeddings import EmbeddingProvider
from app.domain.rag.models import Document, DocumentMetadata


class DocumentIngestionPipeline:
    """Document Ingestion Pipeline to parse, clean, chunk, and index documents into Qdrant."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """Clean raw text by normalizing spacing and removing formatting noise."""
        if not text:
            return ""
        # Replace multiple spaces/newlines with a single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks of length <= chunk_size with word boundary checks and overlap."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return []

        chunks = []
        start = 0
        text_len = len(cleaned)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunks.append(cleaned[start:])
                break

            # Attempt clean split at space boundary near end
            split_idx = cleaned.rfind(" ", start, end)
            if split_idx > start + self.chunk_overlap:
                chunks.append(cleaned[start:split_idx])
                start = split_idx + 1
            else:
                chunks.append(cleaned[start:end])
                start = end - self.chunk_overlap

        return chunks

    def generate_point_id(self, source: str, chunk_index: int) -> str:
        """Generate a deterministic UUID based on document source and chunk index to support version updates."""
        namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "astro.rag.subsystem")
        unique_key = f"{source}::chunk-{chunk_index}"
        return str(uuid.uuid5(namespace, unique_key))

    async def ensure_collection(
        self, client: AsyncQdrantClient, collection_name: str
    ) -> None:
        """Create Qdrant collection if it does not already exist."""
        # Check collection existence
        try:
            collections = await client.get_collections()
            exist = any(c.name == collection_name for c in collections.collections)
        except Exception:
            exist = False

        if not exist:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_provider.dimension,
                    distance=Distance.COSINE,
                ),
            )

    async def ingest_document(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        document: Document,
    ) -> list[str]:
        """Process, clean, chunk, embed, and index a single document.

        Returns list of point IDs upserted.
        """
        await self.ensure_collection(client, collection_name)

        # 1. Clean and chunk
        chunks = self.chunk_text(document.content)
        if not chunks:
            return []

        # 2. Embed chunks
        embeddings = await self.embedding_provider.embed_documents(chunks)

        # 3. Create Points for Qdrant
        points = []
        point_ids = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = self.generate_point_id(document.metadata.source, i)
            point_ids.append(point_id)

            # Flat payload structure for direct indexing and query filtering
            payload = {
                "content": chunk,
                "system": document.metadata.system,
                "methodology": document.metadata.methodology,
                "topic": document.metadata.topic,
                "planet": document.metadata.planet,
                "sign": document.metadata.sign,
                "house": document.metadata.house,
                "domain": document.metadata.domain,
                "source": document.metadata.source,
                "version": document.metadata.version,
                "authority": document.metadata.authority,
                "publication_date": document.metadata.publication_date,
                "chunk_index": i,
                "ingested_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }

            points.append(
                PointStruct(id=point_id, vector=embedding, payload=payload)
            )

        # 4. Upsert points
        await client.upsert(collection_name=collection_name, points=points)
        return point_ids
