from abc import ABC, abstractmethod
from typing import Optional, Callable
import numpy as np

EMBEDDING_BATCH_SIZE = 32  # safe default for BAAI/bge-small-en-v1.5 on CPU


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = EMBEDDING_BATCH_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[list[float]]:
        pass

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class SentenceTransformerEmbeddings(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = EMBEDDING_BATCH_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[list[float]]:
        """
        Embed texts in explicit batches.
        progress_callback(done, total) is called after each batch.
        convert_to_numpy=True avoids an extra tensor→list copy.
        """
        total = len(texts)
        all_embeddings: list[list[float]] = []

        for start in range(0, total, batch_size):
            batch = texts[start : start + batch_size]
            embs = self.model.encode(
                batch,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            all_embeddings.extend(embs.tolist())
            if progress_callback:
                progress_callback(min(start + batch_size, total), total)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        if "bge" in self.model_name.lower():
            text = f"Represent this sentence for searching relevant passages: {text}"
        return self.embed_texts([text])[0]


_embedding_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider(model_name: Optional[str] = None) -> EmbeddingProvider:
    global _embedding_instance
    from app.core.config import get_settings
    settings = get_settings()
    name = model_name or settings.embedding_model
    if _embedding_instance is None:
        _embedding_instance = SentenceTransformerEmbeddings(name)
    return _embedding_instance
