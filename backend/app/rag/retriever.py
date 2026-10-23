from dataclasses import dataclass
from typing import Optional, Callable
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag.chunking import Chunk
from app.rag.embeddings import get_embedding_provider, EMBEDDING_BATCH_SIZE
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client  # noqa: PLW0603 — intentional module-level singleton
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.vector_db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection(name: str = "documents") -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page: int
    section: str
    score: float
    chunk_index: int


def index_chunks(
    chunks: list[Chunk],
    embedding_progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    if not chunks:
        return
    collection = get_collection()
    embedder = get_embedding_provider()

    texts = [c.text for c in chunks]
    embeddings = embedder.embed_texts(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        progress_callback=embedding_progress_callback,
    )
    ids = [c.chunk_id for c in chunks]
    metadatas = [c.to_metadata() for c in chunks]

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=texts[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    logger.info(f"Indexed {len(chunks)} chunks")


def delete_document_chunks(document_id: str) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": document_id})


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    document_ids: Optional[list[str]] = None,
    similarity_threshold: float = 0.0,
) -> list[RetrievedChunk]:
    collection = get_collection()
    embedder = get_embedding_provider()
    query_embedding = embedder.embed_query(query)

    where_filter = None
    if document_ids:
        if len(document_ids) == 1:
            where_filter = {"document_id": document_ids[0]}
        else:
            where_filter = {"document_id": {"$in": document_ids}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count() or 1),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    if not results["ids"] or not results["ids"][0]:
        return chunks

    for cid, doc, meta, dist in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB cosine distance → similarity
        score = 1.0 - dist
        if score < similarity_threshold:
            continue
        chunks.append(
            RetrievedChunk(
                chunk_id=cid,
                document_id=meta.get("document_id", ""),
                document_name=meta.get("document_name", ""),
                text=doc,
                page=int(meta.get("page", 0)),
                section=meta.get("section", ""),
                score=round(score, 4),
                chunk_index=int(meta.get("chunk_index", 0)),
            )
        )

    # Deduplicate near-identical chunks (same document_id + page + chunk_index)
    seen: set[str] = set()
    unique: list[RetrievedChunk] = []
    for c in chunks:
        key = f"{c.document_id}_{c.chunk_index}"
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique
