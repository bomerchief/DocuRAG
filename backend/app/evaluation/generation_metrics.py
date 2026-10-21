"""
Generation quality metrics using local computation.
- Semantic similarity via sentence-transformers (no paid API needed)
- Faithfulness via keyword overlap + LLM-as-judge (optional)
- Hallucination detection via context coverage
"""
from typing import Optional
import re


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using the embedding model."""
    from app.rag.embeddings import get_embedding_provider
    embedder = get_embedding_provider()
    emb_a, emb_b = embedder.embed_texts([text_a, text_b])
    return round(_cosine_similarity(emb_a, emb_b), 4)


def answer_correctness(generated: str, expected: str) -> float:
    """
    Blend of:
    - Exact token overlap (F1)
    - Semantic similarity
    """
    if not generated or not expected:
        return 0.0

    # Token F1
    gen_tokens = set(re.findall(r"\w+", generated.lower()))
    exp_tokens = set(re.findall(r"\w+", expected.lower()))
    if not exp_tokens:
        return 0.0
    precision = len(gen_tokens & exp_tokens) / len(gen_tokens) if gen_tokens else 0.0
    recall = len(gen_tokens & exp_tokens) / len(exp_tokens)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Semantic similarity
    sem = semantic_similarity(generated, expected)

    # Weighted blend
    return round(0.4 * f1 + 0.6 * sem, 4)


def faithfulness(answer: str, context_chunks: list[str]) -> float:
    """
    Measures how well the answer is grounded in the context.
    Uses semantic similarity between answer and combined context.
    """
    if not answer or not context_chunks:
        return 0.0
    combined_context = " ".join(context_chunks)
    return semantic_similarity(answer, combined_context)


def context_relevance(question: str, context_chunks: list[str]) -> float:
    """Average semantic similarity between question and each context chunk."""
    if not context_chunks:
        return 0.0
    from app.rag.embeddings import get_embedding_provider
    embedder = get_embedding_provider()
    q_emb = embedder.embed_query(question)
    chunk_embs = embedder.embed_texts(context_chunks)
    scores = [_cosine_similarity(q_emb, c) for c in chunk_embs]
    return round(sum(scores) / len(scores), 4)


def answer_relevance(question: str, answer: str) -> float:
    """Semantic similarity between question and answer."""
    return semantic_similarity(question, answer)


def detect_hallucination(answer: str, context_chunks: list[str]) -> str:
    """
    Classify answer support level:
    SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED
    Based on faithfulness score thresholds.
    """
    score = faithfulness(answer, context_chunks)
    if score >= 0.70:
        return "SUPPORTED"
    elif score >= 0.45:
        return "PARTIALLY_SUPPORTED"
    return "UNSUPPORTED"


def aggregate_generation_metrics(results: list[dict]) -> dict:
    """
    Each result dict must have:
      generated_answer, expected_answer, context_chunks, question
    """
    correctness_scores, faith_scores, ctx_rel_scores, ans_rel_scores = [], [], [], []
    hallucination_labels = []

    for r in results:
        gen = r.get("generated_answer", "")
        exp = r.get("expected_answer", "")
        ctx = r.get("context_chunks", [])
        q = r.get("question", "")

        correctness_scores.append(answer_correctness(gen, exp))
        faith_scores.append(faithfulness(gen, ctx))
        ctx_rel_scores.append(context_relevance(q, ctx))
        ans_rel_scores.append(answer_relevance(q, gen))
        hallucination_labels.append(detect_hallucination(gen, ctx))

    def avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    unsupported = hallucination_labels.count("UNSUPPORTED")
    partial = hallucination_labels.count("PARTIALLY_SUPPORTED")
    total = len(hallucination_labels) or 1

    return {
        "answer_correctness": avg(correctness_scores),
        "faithfulness": avg(faith_scores),
        "context_relevance": avg(ctx_rel_scores),
        "answer_relevance": avg(ans_rel_scores),
        "hallucination_rate": round((unsupported + 0.5 * partial) / total, 4),
    }
