from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.rag.pipeline import run_rag_pipeline
from app.models.query import QueryLog
from app.utils.hashing import generate_id
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


class ChatRequest(BaseModel):
    question: str
    document_ids: Optional[list[str]] = None
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    prompt_version: Optional[str] = None

    @field_validator('question')
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Question cannot be empty')
        settings = get_settings()
        if len(v) > settings.max_question_length:
            raise ValueError(f'Question exceeds maximum length of {settings.max_question_length} characters')
        return v

    @field_validator('top_k')
    @classmethod
    def top_k_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 20):
            raise ValueError('top_k must be between 1 and 20')
        return v

    @field_validator('similarity_threshold')
    @classmethod
    def threshold_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError('similarity_threshold must be between 0.0 and 1.0')
        return v


class SourceResponse(BaseModel):
    chunk_id: str
    document: str
    page: int
    score: float
    snippet: str
    section: Optional[str] = None


class MetricsResponse(BaseModel):
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    chunks_retrieved: int
    prompt_size: int
    response_length: int


class ChatResponse(BaseModel):
    query_id: str
    answer: str
    sources: list[SourceResponse]
    metrics: MetricsResponse


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):

    try:
        result = run_rag_pipeline(
            question=request.question,
            document_ids=request.document_ids,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            prompt_version=request.prompt_version,
        )
    except RuntimeError as e:
        error_str = str(e)
        if "LLM_UNAVAILABLE" in error_str:
            raise HTTPException(503, detail={
                "error": "LLM_UNAVAILABLE",
                "message": "The local LLM service is unavailable. Please ensure Ollama is running: `ollama serve`",
            })
        raise HTTPException(500, detail={"error": "LLM_ERROR", "message": error_str})

    query_id = generate_id()
    sources = [
        SourceResponse(
            chunk_id=s.chunk_id,
            document=s.document_name,
            page=s.page,
            score=s.score,
            snippet=s.text[:300],
            section=s.section or None,
        )
        for s in result.sources
    ]

    # Persist query log
    log = QueryLog(
        id=query_id,
        question=request.question,
        answer=result.answer,
        document_ids=request.document_ids,
        sources=[s.model_dump() for s in sources],
        retrieval_latency_ms=result.retrieval_latency_ms,
        generation_latency_ms=result.generation_latency_ms,
        total_latency_ms=result.total_latency_ms,
        chunks_retrieved=result.chunks_retrieved,
        prompt_size=result.prompt_size,
        response_length=result.response_length,
        top_k=request.top_k or settings.top_k,
        similarity_threshold=request.similarity_threshold or settings.similarity_threshold,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        status="success",
    )
    db.add(log)
    db.commit()

    return ChatResponse(
        query_id=query_id,
        answer=result.answer,
        sources=sources,
        metrics=MetricsResponse(
            retrieval_latency_ms=round(result.retrieval_latency_ms, 1),
            generation_latency_ms=round(result.generation_latency_ms, 1),
            total_latency_ms=round(result.total_latency_ms, 1),
            chunks_retrieved=result.chunks_retrieved,
            prompt_size=result.prompt_size,
            response_length=result.response_length,
        ),
    )


@router.get("/chat/history")
def get_chat_history(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "question": l.question,
            "answer": l.answer,
            "sources": l.sources,
            "retrieval_latency_ms": l.retrieval_latency_ms,
            "generation_latency_ms": l.generation_latency_ms,
            "total_latency_ms": l.total_latency_ms,
            "chunks_retrieved": l.chunks_retrieved,
            "created_at": str(l.created_at),
        }
        for l in logs
    ]


@router.get("/chat/{query_id}/inspect")
def inspect_query(query_id: str, db: Session = Depends(get_db)):
    """Query inspector — returns full pipeline details for a given query."""
    log = db.query(QueryLog).filter(QueryLog.id == query_id).first()
    if not log:
        raise HTTPException(404, "Query not found")
    return {
        "id": log.id,
        "question": log.question,
        "answer": log.answer,
        "sources": log.sources,
        "metrics": {
            "retrieval_latency_ms": log.retrieval_latency_ms,
            "generation_latency_ms": log.generation_latency_ms,
            "total_latency_ms": log.total_latency_ms,
            "chunks_retrieved": log.chunks_retrieved,
            "prompt_size": log.prompt_size,
            "response_length": log.response_length,
            "top_k": log.top_k,
            "similarity_threshold": log.similarity_threshold,
            "llm_model": log.llm_model,
            "embedding_model": log.embedding_model,
        },
        "created_at": str(log.created_at),
    }


@router.get("/monitoring")
def get_monitoring(db: Session = Depends(get_db)):
    """Performance monitoring summary."""
    logs = db.query(QueryLog).all()
    if not logs:
        return {"total_queries": 0}

    latencies = [l.total_latency_ms for l in logs if l.total_latency_ms]
    ret_latencies = [l.retrieval_latency_ms for l in logs if l.retrieval_latency_ms]
    gen_latencies = [l.generation_latency_ms for l in logs if l.generation_latency_ms]
    failed = sum(1 for l in logs if l.status != "success")

    def avg(lst): return round(sum(lst) / len(lst), 1) if lst else 0
    def pct(lst, p):
        if not lst: return 0
        s = sorted(lst)
        return round(s[int(len(s) * p / 100)], 1)

    return {
        "total_queries": len(logs),
        "failed_requests": failed,
        "avg_latency_ms": avg(latencies),
        "p50_latency_ms": pct(latencies, 50),
        "p95_latency_ms": pct(latencies, 95),
        "avg_retrieval_latency_ms": avg(ret_latencies),
        "avg_generation_latency_ms": avg(gen_latencies),
    }
