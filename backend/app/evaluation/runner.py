"""
Evaluation runner: executes the full RAG pipeline against an eval dataset
and computes all retrieval + generation metrics.
"""
from typing import Optional

from app.evaluation.dataset import EvalQuestion
from app.evaluation.retrieval_metrics import (
    recall_at_k, precision_at_k, hit_rate, reciprocal_rank,
    aggregate_retrieval_metrics,
)
from app.evaluation.generation_metrics import (
    answer_correctness, faithfulness, context_relevance,
    answer_relevance, detect_hallucination, aggregate_generation_metrics,
)
from app.rag.pipeline import run_rag_pipeline
from app.core.logging import get_logger

logger = get_logger(__name__)


def evaluate_single(
    question: EvalQuestion,
    document_ids: Optional[list[str]] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    prompt_version: str = "v1",
) -> dict:
    result = run_rag_pipeline(
        question=question.question,
        document_ids=document_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        prompt_version=prompt_version,
    )

    retrieved_ids = [c.chunk_id for c in result.sources]
    context_texts = [c.text for c in result.sources]
    # Rich context metadata for UI inspection
    context_chunks = [
        {
            "chunk_id": c.chunk_id,
            "document": c.document_name,
            "page": c.page,
            "section": c.section,
            "score": c.score,
            "text": c.text,
        }
        for c in result.sources
    ]

    rr = reciprocal_rank(question.relevant_chunk_ids, retrieved_ids)
    r_at_k = recall_at_k(question.relevant_chunk_ids, retrieved_ids, top_k)
    p_at_k = precision_at_k(question.relevant_chunk_ids, retrieved_ids, top_k)
    hit = hit_rate(question.relevant_chunk_ids, retrieved_ids)
    faith = faithfulness(result.answer, context_texts)
    correctness = answer_correctness(result.answer, question.expected_answer)
    hallucination = detect_hallucination(result.answer, context_texts)

    return {
        "question": question.question,
        "expected_answer": question.expected_answer,
        "generated_answer": result.answer,
        "relevant_chunk_ids": question.relevant_chunk_ids,
        "retrieved_chunk_ids": retrieved_ids,
        "retrieved_scores": [c.score for c in result.sources],
        "context_chunks": context_chunks,
        "recall_at_k": r_at_k,
        "precision_at_k": p_at_k,
        "reciprocal_rank": rr,
        "hit": int(hit),
        "faithfulness": faith,
        "answer_correctness": correctness,
        "hallucination_label": hallucination,
        "retrieval_latency_ms": result.retrieval_latency_ms,
        "generation_latency_ms": result.generation_latency_ms,
        "total_latency_ms": result.total_latency_ms,
        "category": question.category,
        "difficulty": question.difficulty,
    }


def run_evaluation(
    questions: list[EvalQuestion],
    document_ids: Optional[list[str]] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    prompt_version: str = "v1",
    progress_tracker: Optional[dict] = None,
) -> dict:
    per_question = []
    for i, q in enumerate(questions):
        logger.info(f"Evaluating question {i+1}/{len(questions)}: {q.question[:60]}")
        if progress_tracker is not None:
            progress_tracker["current"] = i
        try:
            result = evaluate_single(q, document_ids, top_k, similarity_threshold, prompt_version)
        except Exception as e:
            logger.error(f"Failed to evaluate question: {e}")
            result = {
                "question": q.question,
                "expected_answer": q.expected_answer,
                "generated_answer": "",
                "relevant_chunk_ids": q.relevant_chunk_ids,
                "retrieved_chunk_ids": [],
                "retrieved_scores": [],
                "context_chunks": [],
                "recall_at_k": 0.0,
                "precision_at_k": 0.0,
                "reciprocal_rank": 0.0,
                "hit": 0,
                "faithfulness": 0.0,
                "answer_correctness": 0.0,
                "hallucination_label": "UNSUPPORTED",
                "retrieval_latency_ms": 0.0,
                "generation_latency_ms": 0.0,
                "total_latency_ms": 0.0,
                "category": q.category,
                "difficulty": q.difficulty,
                "error": str(e),
            }
        per_question.append(result)
        if progress_tracker is not None:
            progress_tracker["current"] = i + 1

    retrieval_agg = aggregate_retrieval_metrics(per_question)
    generation_agg = aggregate_generation_metrics(per_question)

    latencies = [r["total_latency_ms"] for r in per_question if r["total_latency_ms"] > 0]
    ret_latencies = [r["retrieval_latency_ms"] for r in per_question]
    gen_latencies = [r["generation_latency_ms"] for r in per_question]

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    def percentile(lst, p):
        if not lst:
            return 0.0
        s = sorted(lst)
        idx = int(len(s) * p / 100)
        return round(s[min(idx, len(s) - 1)], 2)

    latency_metrics = {
        "avg_latency_ms": avg(latencies),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "avg_retrieval_latency_ms": avg(ret_latencies),
        "avg_generation_latency_ms": avg(gen_latencies),
    }

    return {
        **retrieval_agg,
        **generation_agg,
        **latency_metrics,
        "num_questions": len(questions),
        "question_results": per_question,
    }
