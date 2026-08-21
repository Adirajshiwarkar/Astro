import asyncio
import logging
from typing import List

from app.domain.rag.embeddings import HuggingFaceEmbeddingProvider
from app.domain.rag.engine import RAGSubsystem
from app.domain.rag.models import Document, DocumentMetadata
from app.services.qdrant import qdrant_service

logger = logging.getLogger("app.domain.rag.seed")

PRETRAINED_ASTROLOGY_DATA: List[Document] = [
    Document(
        content=(
            "Sun Transit in 10th House (Career & Public Recognition): "
            "When the transiting Sun enters the 10th house (Midheaven), it illuminates your professional reputation, "
            "career ambitions, and authority. This is a powerful period for career advancements, promotions, "
            "and public leadership. Combined with Mercury (Budhaditya Yoga), it bestows high analytical skill, "
            "decisive management, and success in executive roles."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="Transits",
            planet="Sun",
            house="10",
            domain="career",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Jupiter Transits & Gaja Kesari Yoga (Growth, Fortune & Wisdom): "
            "Jupiter's transit over angles (1st, 4th, 7th, 10th houses) or forming a quadrant relationship with the Moon "
            "activates Gaja Kesari Yoga. This brings expansive growth, financial stability, higher learning, "
            "and protection against negative transits. It is auspicious for marriage, business partnerships, and investments."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="Yogas",
            planet="Jupiter",
            domain="finance",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Saturn Transits & Sade Sati (Discipline, Structure & Resilience): "
            "Saturn transits through the 12th, 1st, and 2nd houses relative to the natal Moon define the 7.5-year Sade Sati period. "
            "While requiring hard work, discipline, and emotional maturity, Saturn rewards persistence with permanent, "
            "unshakable career stability and spiritual grounding."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="Dasha & Transits",
            planet="Saturn",
            domain="career",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Venus Transits in 7th & 11th Houses (Relationships & Financial Gains): "
            "Venus transiting the 7th house enhances marital harmony, romantic connection, and business alliances. "
            "In the 11th house, Venus brings steady gains from social networks, creative projects, and strategic investments."
        ),
        metadata=DocumentMetadata(
            system="Western",
            methodology="Placidus",
            topic="Transits",
            planet="Venus",
            house="7",
            domain="relationship",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Mars Energy & 3rd / 6th House Placements (Courage & Overcoming Obstacles): "
            "Mars in upachaya houses (3rd, 6th, 10th, 11th) gives immense drive, athletic stamina, competitive edge, "
            "and victory over opposition. In business, it signifies bold initiatives, marketing prowess, and decisive action."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="House Placements",
            planet="Mars",
            house="6",
            domain="health",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Mercury & 2nd / 5th House (Intellect, Speech & Wealth): "
            "Mercury governing or transiting the 2nd (speech, family wealth) and 5th (intelligence, speculation) "
            "enhances financial forecasting, coding, writing, and strategic negotiations. It creates sharp intellect and adaptability."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="House Placements",
            planet="Mercury",
            house="5",
            domain="finance",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Moon & 4th House (Mind, Inner Peace & Property): "
            "A well-placed transiting Moon in the 4th house brings emotional contentment, mental clarity, "
            "harmony in domestic life, and opportunities in real estate, home investments, or motherly support."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="House Placements",
            planet="Moon",
            house="4",
            domain="relationship",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
    Document(
        content=(
            "Rahu & Ketu Axis Transits (Karmic Shifts & Innovation): "
            "Rahu in the 10th or 11th house generates rapid career growth, technological innovation, and unconventional success, "
            "while Ketu in the 4th or 5th house encourages spiritual introspection, detachment, and deep research."
        ),
        metadata=DocumentMetadata(
            system="Vedic",
            methodology="Parashari",
            topic="Nodes",
            planet="Rahu",
            house="10",
            domain="career",
            source="Pretrained Astrology Core Corpus v2.0",
        ),
    ),
]


async def seed_pretrained_astrology_knowledge() -> int:
    """Embed and index the pretrained astrological knowledge base into Qdrant if collection is empty."""
    await qdrant_service.connect()

    try:
        col_info = qdrant_service.client.get_collection("astrology_kb")
        if col_info and getattr(col_info, "points_count", 0) > 0:
            logger.info(f"[KB SEED] Collection 'astrology_kb' already initialized with {col_info.points_count} vectors. Skipping redundant embedding.")
            return col_info.points_count
    except Exception:
        pass

    logger.info("[KB SEED] Initializing pretrained astrology embedding dataset...")
    embedding_provider = HuggingFaceEmbeddingProvider()
    rag_subsystem = RAGSubsystem(
        client=qdrant_service.client,
        embedding_provider=embedding_provider,
    )

    point_ids = await rag_subsystem.ingest_documents(PRETRAINED_ASTROLOGY_DATA)
    logger.info(
        f"[KB SEED SUCCESS] Embedded and indexed {len(PRETRAINED_ASTROLOGY_DATA)} pretrained documents into Qdrant ({len(point_ids)} chunks)."
    )
    return len(PRETRAINED_ASTROLOGY_DATA)


if __name__ == "__main__":
    asyncio.run(seed_pretrained_astrology_knowledge())
