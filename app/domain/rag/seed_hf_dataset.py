import asyncio
import logging
from typing import List

from datasets import load_dataset

from app.domain.rag.embeddings import HuggingFaceEmbeddingProvider
from app.domain.rag.engine import RAGSubsystem
from app.domain.rag.models import Document, DocumentMetadata
from app.services.qdrant import qdrant_service

logger = logging.getLogger("app.domain.rag.seed_hf")


async def seed_hf_astrology_compatibility_dataset(limit: int = 500) -> int:
    """
    Load 'GuruDharamSingh/astrology-compatibility' from Hugging Face Datasets,
    convert entries to Document objects, compute embeddings, and index into Qdrant Vector DB.
    Skips embedding if vectors are already present in Qdrant.
    """
    await qdrant_service.connect()

    try:
        col_info = qdrant_service.client.get_collection("astrology_kb")
        if col_info and getattr(col_info, "points_count", 0) > 0:
            logger.info(f"[HF DATASET SEED] Qdrant collection 'astrology_kb' already contains {col_info.points_count} vectors. Skipping redundant embedding computation.")
            return col_info.points_count
    except Exception:
        pass

    logger.info("[HF DATASET SEED] Loading dataset 'GuruDharamSingh/astrology-compatibility' from Hugging Face Hub...")
    try:
        hf_ds = load_dataset("GuruDharamSingh/astrology-compatibility")
        train_split = hf_ds.get("train", [])
    except Exception as err:
        logger.error(f"[HF DATASET SEED FAILED] Could not load dataset from Hugging Face: {err}")
        return 0

    documents: List[Document] = []
    max_items = min(limit, len(train_split))
    logger.info(f"[HF DATASET SEED] Processing first {max_items} records from dataset...")

    for i in range(max_items):
        item = train_split[i]
        instruction = item.get("instruction", "")
        context_input = item.get("input", "")
        output_text = item.get("output", "")

        combined_content = (
            f"Query/Topic: {instruction}\n"
            f"Focus Context: {context_input}\n"
            f"Astrological Analysis: {output_text}"
        )

        doc = Document(
            content=combined_content,
            metadata=DocumentMetadata(
                system="Both",
                methodology="Parashari & Synastry",
                topic="Compatibility & Transit Readings",
                domain="relationship",
                source="GuruDharamSingh/astrology-compatibility",
                authority="HuggingFace Open Astrology Corpus",
            ),
        )
        documents.append(doc)

    embedding_provider = HuggingFaceEmbeddingProvider()
    rag_subsystem = RAGSubsystem(
        client=qdrant_service.client,
        embedding_provider=embedding_provider,
    )

    logger.info(f"[HF DATASET SEED] Generating vector embeddings for {len(documents)} compatibility documents...")
    point_ids = await rag_subsystem.ingest_documents(documents)
    logger.info(
        f"[HF DATASET SEED SUCCESS] Successfully embedded and indexed {len(documents)} compatibility documents into Qdrant Vector DB ({len(point_ids)} point vectors)."
    )
    return len(documents)


if __name__ == "__main__":
    asyncio.run(seed_hf_astrology_compatibility_dataset(limit=500))
