from dataclasses import dataclass, field
from typing import Optional

from app.rag.retriever import retrieve_chunks, RetrievedChunk
from app.rag.generator import get_llm_provider
from app.rag.prompts import format_prompt
from app.utils.timing import timer
from app.utils.text import truncate_text
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResult:
    answer: str
    sources: list[RetrievedChunk]
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    chunks_retrieved: int
    prompt_size: int
    response_length: int
    prompt_version: str


def run_rag_pipeline(
    question: str,
    document_ids: Optional[list[str]] = None,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    prompt_version: Optional[str] = None,
    temperature: Optional[float] = None,
) -> RAGResult:
    settings = get_settings()
    top_k = top_k or settings.top_k
    similarity_threshold = similarity_threshold if similarity_threshold is not None else settings.similarity_threshold
    prompt_version = prompt_version or settings.prompt_version
    temperature = temperature if temperature is not None else settings.temperature

    # Retrieval
    with timer() as retrieval_time:
        chunks = retrieve_chunks(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
            similarity_threshold=similarity_threshold,
        )

    if not chunks:
        return RAGResult(
            answer="I couldn't find this information in the provided documents.",
            sources=[],
            retrieval_latency_ms=retrieval_time["elapsed_ms"],
            generation_latency_ms=0.0,
            total_latency_ms=retrieval_time["elapsed_ms"],
            chunks_retrieved=0,
            prompt_size=0,
            response_length=0,
            prompt_version=prompt_version,
        )

    # Build prompt
    prompt = format_prompt(question, chunks, version=prompt_version)
    prompt_size = len(prompt)

    # Generation
    llm = get_llm_provider()
    with timer() as gen_time:
        answer = llm.generate(prompt, temperature=temperature)

    total_ms = retrieval_time["elapsed_ms"] + gen_time["elapsed_ms"]

    logger.info(
        "RAG pipeline complete",
        extra={
            "question_preview": truncate_text(question, 80),
            "chunks_retrieved": len(chunks),
            "retrieval_latency_ms": round(retrieval_time["elapsed_ms"], 1),
            "generation_latency_ms": round(gen_time["elapsed_ms"], 1),
            "total_latency_ms": round(total_ms, 1),
        },
    )

    return RAGResult(
        answer=answer,
        sources=chunks,
        retrieval_latency_ms=retrieval_time["elapsed_ms"],
        generation_latency_ms=gen_time["elapsed_ms"],
        total_latency_ms=total_ms,
        chunks_retrieved=len(chunks),
        prompt_size=prompt_size,
        response_length=len(answer),
        prompt_version=prompt_version,
    )
