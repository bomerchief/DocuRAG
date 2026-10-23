from dataclasses import dataclass, field
from typing import Optional

from app.rag.retriever import retrieve_chunks, RetrievedChunk
from app.rag.generator import get_llm_provider
from app.rag.prompts import format_prompt
from app.rag.web_search import search_web, WebResult
from app.utils.timing import timer
from app.utils.text import truncate_text
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResult:
    answer: str
    sources: list[RetrievedChunk]
    web_results: list[WebResult]
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

    # Web search
    web_results: list[WebResult] = []
    if settings.web_search_enabled:
        with timer() as web_time:
            web_results = search_web(question, max_results=settings.web_search_max_results)

    # Retrieval
    with timer() as retrieval_time:
        chunks = retrieve_chunks(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
            similarity_threshold=similarity_threshold,
        )

    # If no docs and no web results, return early
    if not chunks and not web_results:
        return RAGResult(
            answer="I couldn't find relevant information from documents or the web.",
            sources=[],
            web_results=[],
            retrieval_latency_ms=retrieval_time["elapsed_ms"],
            generation_latency_ms=0.0,
            total_latency_ms=retrieval_time["elapsed_ms"],
            chunks_retrieved=0,
            prompt_size=0,
            response_length=0,
            prompt_version=prompt_version,
        )

    # Use v3 prompt if web search is enabled, else fall back to configured version
    active_version = "v3" if settings.web_search_enabled else prompt_version
    prompt = format_prompt(question, chunks, version=active_version, web_results=web_results)
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
            "web_results": len(web_results),
            "retrieval_latency_ms": round(retrieval_time["elapsed_ms"], 1),
            "generation_latency_ms": round(gen_time["elapsed_ms"], 1),
            "total_latency_ms": round(total_ms, 1),
        },
    )

    return RAGResult(
        answer=answer,
        sources=chunks,
        web_results=web_results,
        retrieval_latency_ms=retrieval_time["elapsed_ms"],
        generation_latency_ms=gen_time["elapsed_ms"],
        total_latency_ms=total_ms,
        chunks_retrieved=len(chunks),
        prompt_size=prompt_size,
        response_length=len(answer),
        prompt_version=active_version,
    )
