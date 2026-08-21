import asyncio
import json
import logging

from app.domain.rag.embeddings import HuggingFaceEmbeddingProvider
from app.domain.rag.engine import RAGSubsystem
from app.domain.rag.models import RetrievalRequest
from app.services.qdrant import qdrant_service

logger = logging.getLogger("app.domain.rag.inspect")


async def inspect_qdrant_embedded_dataset(sample_query: str = "compatibility between Pisces and Gemini"):
    """Connect to Qdrant, retrieve collection metadata, count points, and display sample vector payloads."""
    print("=" * 80)
    print(" QDRANT VECTOR DATABASE EMBEDDED DATASET INSPECTOR")
    print("=" * 80)

    await qdrant_service.connect()
    client = qdrant_service.client

    # 1. Fetch collection info
    try:
        collections_res = await client.get_collections()
        print(f"\n[1] Active Collections in Qdrant: {[c.name for c in collections_res.collections]}")
    except Exception as err:
        print(f"Error fetching Qdrant collections: {err}")
        return

    collection_name = "astrology_knowledge_base"

    # 2. Perform RAG Vector Search for sample documents
    print(f"\n[2] Executing Vector Search Query: '{sample_query}'")
    embedding_provider = HuggingFaceEmbeddingProvider()
    rag_subsystem = RAGSubsystem(client=client, embedding_provider=embedding_provider)

    req = RetrievalRequest(query=sample_query, limit=5)
    results = await rag_subsystem.retrieve(request=req)

    print(f"\n[3] Retrieved {len(results)} Embedded Vector Matches from Qdrant:")
    print("-" * 80)
    for i, res in enumerate(results, start=1):
        print(f"\n--- Match #{i} (Similarity Score: {res.score:.4f}) ---")
        print(f"Source: {res.source}")
        print(f"System / Domain: {res.system} | {res.domain}")
        print(f"Content Payload Snippet:\n{res.content}")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(inspect_qdrant_embedded_dataset())
