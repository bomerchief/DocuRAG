from dataclasses import dataclass, field
from typing import Optional
from app.rag.ingestion import ParsedDocument
from app.utils.hashing import chunk_id
from app.utils.text import count_tokens_approx


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page: int
    section: Optional[str]
    chunk_index: int
    token_count: int = 0

    def to_metadata(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page": self.page,
            "section": self.section or "",
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
        }


def chunk_document(
    doc: ParsedDocument,
    document_id: str,
    document_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """
    Split document pages into overlapping token-based chunks.
    Preserves page and section metadata per chunk.
    """
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in doc.pages:
        words = page.text.split()
        if not words:
            continue

        # Approximate tokens ≈ words for splitting purposes
        step = max(1, chunk_size - chunk_overlap)
        start = 0

        while start < len(words):
            end = start + chunk_size
            window = words[start:end]
            text = " ".join(window)
            token_count = count_tokens_approx(text)

            cid = chunk_id(document_id, chunk_index)
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    document_id=document_id,
                    document_name=document_name,
                    text=text,
                    page=page.page_number,
                    section=page.section,
                    chunk_index=chunk_index,
                    token_count=token_count,
                )
            )
            chunk_index += 1
            if end >= len(words):
                break
            start += step

    return chunks
