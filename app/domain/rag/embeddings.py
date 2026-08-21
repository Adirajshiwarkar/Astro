import abc
import hashlib
import logging
from typing import Sequence
import numpy as np

logger = logging.getLogger("app.domain.rag.embeddings")


class EmbeddingProvider(abc.ABC):
    """Abstract base class for embedding providers."""

    @abc.abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        pass

    @abc.abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a list of document strings."""
        pass

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """The dimension of generated embeddings."""
        pass


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Pretrained Hugging Face / Sentence Transformers embedding provider for semantic vector representation."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._dimension = 384
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"[EMBEDDING PROVIDER] Loaded pretrained model '{model_name}' (dimension={self._dimension})")
        except Exception as e:
            logger.warning(f"[EMBEDDING PROVIDER] Could not load SentenceTransformer '{model_name}': {e}. Using deterministic fallback.")

    async def embed_query(self, text: str) -> list[float]:
        if self._model:
            try:
                vec = self._model.encode(text, convert_to_numpy=True)
                return [float(x) for x in vec]
            except Exception as e:
                logger.warning(f"[EMBEDDING PROVIDER] Error generating embedding: {e}")

        # Deterministic fallback
        return await MockEmbeddingProvider(self._dimension).embed_query(text)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model and texts:
            try:
                vecs = self._model.encode(list(texts), convert_to_numpy=True)
                return [[float(x) for x in v] for v in vecs]
            except Exception as e:
                logger.warning(f"[EMBEDDING PROVIDER] Error generating batch embeddings: {e}")

        return [await self.embed_query(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider that deterministically generates embeddings using text hashing."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    async def embed_query(self, text: str) -> list[float]:
        cleaned = " ".join(text.lower().split())
        hasher = hashlib.md5(cleaned.encode("utf-8"))
        seed = int(hasher.hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        vector = rng.normal(0, 1, self._dimension)
        norm = np.linalg.norm(vector)
        normalized = (vector / norm).tolist() if norm > 0 else vector.tolist()
        return [float(x) for x in normalized]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.embed_query(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
