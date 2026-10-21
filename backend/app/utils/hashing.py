import hashlib
import html
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def hash_bytes(data: bytes) -> str:
    """SHA-256 hex digest of raw bytes (for file dedup)."""
    return hashlib.sha256(data).hexdigest()


def chunk_id(document_id: str, index: int) -> str:
    safe_id = html.escape(document_id[:8])
    return f"{safe_id}_chunk_{index:04d}"
