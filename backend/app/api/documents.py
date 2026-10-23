import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from werkzeug.utils import secure_filename
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.document import Document
from app.rag.ingestion import parse_document, SUPPORTED_EXTENSIONS, UPLOAD_DIR as INGESTION_UPLOAD_DIR
from app.rag.chunking import chunk_document
from app.rag.retriever import index_chunks, delete_document_chunks
from app.utils.hashing import generate_id, hash_bytes
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

UPLOAD_DIR = INGESTION_UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentResponse(BaseModel):
    id: str
    name: str
    file_type: str
    file_size_bytes: int
    num_chunks: int
    status: str
    error_message: Optional[str]
    created_at: str
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    embedding_model: Optional[str]
    ingestion_stage: Optional[str] = None
    ingestion_progress: Optional[int] = None
    file_hash: Optional[str] = None


def _set_stage(db: Session, doc_id: str, stage: str, progress: int) -> None:
    """Update ingestion stage + progress and commit immediately."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        doc.ingestion_stage = stage
        doc.ingestion_progress = progress
        db.commit()


def _process_document(doc_id: str, file_path: str, file_name: str) -> None:
    """Background task: parse → chunk → embed → index with timing logs and progress."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    t_total = time.perf_counter()

    try:
        # ── Stage 1: Extract text ──────────────────────────────────────────
        _set_stage(db, doc_id, "Extracting text...", 10)
        t0 = time.perf_counter()
        parsed = parse_document(file_path, file_name)
        t_parse = time.perf_counter() - t0
        num_pages = len(parsed.pages)
        logger.info(f"[INGEST] PDF extraction: {t_parse:.2f}s | Pages: {num_pages}")

        # ── Stage 2: Chunking ──────────────────────────────────────────────
        _set_stage(db, doc_id, "Creating chunks...", 25)
        t0 = time.perf_counter()
        chunks = chunk_document(
            parsed,
            document_id=doc_id,
            document_name=file_name,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        t_chunk = time.perf_counter() - t0
        num_chunks = len(chunks)
        logger.info(f"[INGEST] Chunks created: {num_chunks} | Chunking time: {t_chunk:.2f}s")

        if not chunks:
            raise ValueError("Document produced no chunks after parsing.")

        # ── Stage 3: Embedding ─────────────────────────────────────────────
        _set_stage(db, doc_id, f"Generating embeddings: 0 / {num_chunks}", 30)

        def _embedding_progress(done: int, total: int) -> None:
            pct = 30 + int((done / total) * 55)  # 30→85%
            _set_stage(db, doc_id, f"Generating embeddings: {done} / {total}", pct)

        t0 = time.perf_counter()
        # index_chunks handles batched embedding + vector upsert
        index_chunks(chunks, embedding_progress_callback=_embedding_progress)
        t_embed_and_store = time.perf_counter() - t0
        logger.info(f"[INGEST] Embedding + vector insertion: {t_embed_and_store:.2f}s")

        # ── Stage 4: Finalise DB record ────────────────────────────────────
        _set_stage(db, doc_id, "Storing vectors...", 90)
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if doc_record:
            doc_record.num_chunks = num_chunks
            doc_record.status = "ready"
            doc_record.ingestion_stage = "Completed"
            doc_record.ingestion_progress = 100
            doc_record.chunk_size = settings.chunk_size
            doc_record.chunk_overlap = settings.chunk_overlap
            doc_record.embedding_model = settings.embedding_model
            db.commit()

        t_total_s = time.perf_counter() - t_total
        logger.info(
            f"[INGEST] Total ingestion: {t_total_s:.2f}s | "
            f"Pages: {num_pages} | Chunks: {num_chunks} | "
            f"Embed+store: {t_embed_and_store:.2f}s"
        )

    except Exception as e:
        logger.error(f"[INGEST] Document processing failed for {doc_id}: {e}")
        # Clean up any partial vectors so the user can retry cleanly
        try:
            delete_document_chunks(doc_id)
        except Exception as cleanup_err:
            logger.warning(f"[INGEST] Partial vector cleanup failed: {cleanup_err}")

        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if doc_record:
            doc_record.status = "error"
            doc_record.error_message = str(e)
            doc_record.ingestion_stage = "Failed"
            doc_record.ingestion_progress = 0
            db.commit()
    finally:
        db.close()


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")

    safe_name = secure_filename(file.filename)
    if not safe_name:
        raise HTTPException(400, "Invalid filename")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(413, f"File too large ({size_mb:.1f} MB). Max: {settings.max_file_size_mb} MB")

    # ── Duplicate detection ────────────────────────────────────────────────
    file_hash = hash_bytes(content)
    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing and existing.status == "ready":
        raise HTTPException(
            409,
            f"This file has already been uploaded as '{existing.name}' "
            f"({existing.num_chunks} chunks). Delete it first to re-process."
        )

    doc_id = generate_id()
    save_path = (UPLOAD_DIR / f"{doc_id}{ext}").resolve()
    if not str(save_path).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(400, "Invalid file path")
    save_path.write_bytes(content)

    doc = Document(
        id=doc_id,
        name=safe_name,
        file_type=ext.lstrip("."),
        file_size_bytes=len(content),
        file_hash=file_hash,
        status="processing",
        ingestion_stage="Uploading...",
        ingestion_progress=5,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_document, doc_id, str(save_path), safe_name)

    return _to_response(doc)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_to_response(d) for d in docs]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return _to_response(doc)


@router.get("/documents/{doc_id}/progress")
def get_document_progress(doc_id: str, db: Session = Depends(get_db)):
    """Lightweight progress polling endpoint."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id,
        "status": doc.status,
        "ingestion_stage": doc.ingestion_stage,
        "ingestion_progress": doc.ingestion_progress,
        "num_chunks": doc.num_chunks,
        "error_message": doc.error_message,
    }


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    delete_document_chunks(doc_id)
    for ext in SUPPORTED_EXTENSIONS:
        p = UPLOAD_DIR / f"{doc_id}{ext}"
        if p.exists():
            p.unlink()
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


def _to_response(d: Document) -> DocumentResponse:
    return DocumentResponse(
        id=d.id,
        name=d.name,
        file_type=d.file_type,
        file_size_bytes=d.file_size_bytes,
        num_chunks=d.num_chunks,
        status=d.status,
        error_message=d.error_message,
        created_at=str(d.created_at),
        chunk_size=d.chunk_size,
        chunk_overlap=d.chunk_overlap,
        embedding_model=d.embedding_model,
        ingestion_stage=d.ingestion_stage,
        ingestion_progress=d.ingestion_progress,
        file_hash=d.file_hash,
    )
