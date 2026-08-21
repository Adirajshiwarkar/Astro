import re
from typing import Optional, Sequence
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.domain.rag.embeddings import EmbeddingProvider
from app.domain.rag.models import RetrievalRequest, RetrievalResult


class KnowledgeRetrievalEngine:
    """Retrieval Engine for executing semantic searches with metadata filtering and routing."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.embedding_provider = embedding_provider

    def route_query_system(self, query: str) -> Optional[str]:
        """Auto-detect system context from query terms to prevent cross-system contamination."""
        q_lower = query.lower()

        # Specific terms defining Vedic astrology
        vedic_terms = [
            "bhava", "graha", "rashi", "raci", "dasha", "dasa", "vimshottari",
            "lagna", "lahiri", "ayanamsa", "ayanamsha", "yuvati", "mesha",
            "vrishabha", "mithuna", "karka", "simha", "kanya", "tula",
            "vrishchika", "dhanu", "makara", "kumbha", "meena", "surya",
            "chandra", "mangala", "budha", "guru", "shukra", "shani",
            "rahu", "ketu", "kundli", "parashara", "parashari"
        ]

        # Specific terms defining Western astrology
        western_terms = [
            "house", "planet", "sign", "aspect", "conjunction", "trine",
            "sextile", "opposition", "square", "placidus", "koch",
            "tropical", "orb", "retrograde"
        ]

        # Specific terms defining Numerology
        numerology_terms = [
            "personal year", "life path", "soul urge", "numerology",
            "expression number", "birth day number"
        ]

        has_vedic = any(term in q_lower for term in vedic_terms)
        has_western = any(term in q_lower for term in western_terms)
        has_numerology = any(term in q_lower for term in numerology_terms)

        # Enforce route only if one system is distinctively present
        if has_vedic and not has_western and not has_numerology:
            return "Vedic"
        elif has_western and not has_vedic and not has_numerology:
            return "Western"
        elif has_numerology and not has_western and not has_vedic:
            return "Numerology"

        return None

    def build_qdrant_filter(self, request: RetrievalRequest) -> Optional[Filter]:
        """Map retrieval request filters to Qdrant's Filter schema."""
        conditions = []

        # Auto-detect target system if not explicitly set
        routed_system = request.system or self.route_query_system(request.query)
        if routed_system:
            conditions.append(
                FieldCondition(
                    key="system", match=MatchValue(value=routed_system)
                )
            )

        # Apply other explicit filters
        if request.methodology:
            conditions.append(
                FieldCondition(
                    key="methodology", match=MatchValue(value=request.methodology)
                )
            )
        if request.domain:
            conditions.append(
                FieldCondition(
                    key="domain", match=MatchValue(value=request.domain)
                )
            )
        if request.planet:
            conditions.append(
                FieldCondition(
                    key="planet", match=MatchValue(value=request.planet)
                )
            )
        if request.sign:
            conditions.append(
                FieldCondition(key="sign", match=MatchValue(value=request.sign))
            )
        if request.house:
            conditions.append(
                FieldCondition(
                    key="house", match=MatchValue(value=request.house)
                )
            )

        if not conditions:
            return None

        return Filter(must=conditions)

    def calculate_lexical_similarity(self, query: str, content: str) -> float:
        """Calculate word-level Jaccard similarity to serve as a lexical matching score."""
        q_words = set(re.findall(r"\b\w+\b", query.lower()))
        c_words = set(re.findall(r"\b\w+\b", content.lower()))
        if not q_words:
            return 0.0
        intersection = q_words.intersection(c_words)
        union = q_words.union(c_words)
        return len(intersection) / len(union)

    def hybrid_rerank(
        self,
        query: str,
        results: Sequence[RetrievalResult],
        vector_weight: float = 0.7,
        lexical_weight: float = 0.3,
    ) -> list[RetrievalResult]:
        """Rerank search results using a hybrid score combining vector similarity and lexical overlap."""
        reranked = []
        for res in results:
            lexical_score = self.calculate_lexical_similarity(query, res.content)
            res.rerank_score = (vector_weight * res.score) + (
                lexical_weight * lexical_score
            )
            reranked.append(res)

        return sorted(reranked, key=lambda x: x.rerank_score or 0.0, reverse=True)

    async def retrieve(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        request: RetrievalRequest,
    ) -> list[RetrievalResult]:
        """Perform semantic search, filter by metadata context, and apply optional reranking."""
        # 1. Embed query
        query_vector = await self.embedding_provider.embed_query(request.query)

        # 2. Build filter
        qdrant_filter = self.build_qdrant_filter(request)

        # 3. Search Qdrant
        response = await client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=request.limit,
        )
        search_results = response.points

        # 4. Map to models
        mapped_results = []
        for item in search_results:
            payload = item.payload or {}
            mapped_results.append(
                RetrievalResult(
                    content=payload.get("content", ""),
                    score=item.score,
                    system=payload.get("system", "Unknown"),
                    methodology=payload.get("methodology"),
                    topic=payload.get("topic"),
                    planet=payload.get("planet"),
                    sign=payload.get("sign"),
                    house=payload.get("house"),
                    domain=payload.get("domain"),
                    source=payload.get("source", "Unknown"),
                    version=payload.get("version", "1.0.0"),
                    authority=payload.get("authority"),
                    publication_date=payload.get("publication_date"),
                )
            )

        # 5. Optional Reranking
        if request.rerank:
            return self.hybrid_rerank(request.query, mapped_results)

        return mapped_results
