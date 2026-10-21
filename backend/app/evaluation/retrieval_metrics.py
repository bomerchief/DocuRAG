from typing import Optional


def recall_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    """Fraction of relevant chunks found in top-k retrieved."""
    if not relevant:
        return 0.0
    top_k = set(retrieved[:k])
    hits = sum(1 for r in relevant if r in top_k)
    return hits / len(relevant)


def precision_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    """Fraction of top-k retrieved that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for r in top_k if r in relevant_set)
    return hits / k


def hit_rate(relevant: list[str], retrieved: list[str]) -> float:
    """1 if any relevant chunk appears in retrieved, else 0."""
    relevant_set = set(relevant)
    return 1.0 if any(r in relevant_set for r in retrieved) else 0.0


def reciprocal_rank(relevant: list[str], retrieved: list[str]) -> float:
    """1/rank of first relevant chunk in retrieved list."""
    relevant_set = set(relevant)
    for i, r in enumerate(retrieved, 1):
        if r in relevant_set:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(rr_scores: list[float]) -> float:
    if not rr_scores:
        return 0.0
    return sum(rr_scores) / len(rr_scores)


def aggregate_retrieval_metrics(results: list[dict]) -> dict:
    """
    Each result dict must have keys:
      relevant_chunk_ids, retrieved_chunk_ids
    """
    rr_scores, hits = [], []
    r1, r3, r5, r10 = [], [], [], []
    p3, p5, p10 = [], [], []

    for r in results:
        rel = r["relevant_chunk_ids"]
        ret = r["retrieved_chunk_ids"]
        r1.append(recall_at_k(rel, ret, 1))
        r3.append(recall_at_k(rel, ret, 3))
        r5.append(recall_at_k(rel, ret, 5))
        r10.append(recall_at_k(rel, ret, 10))
        p3.append(precision_at_k(rel, ret, 3))
        p5.append(precision_at_k(rel, ret, 5))
        p10.append(precision_at_k(rel, ret, 10))
        hits.append(hit_rate(rel, ret))
        rr_scores.append(reciprocal_rank(rel, ret))

    def avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    return {
        "recall_at_1": avg(r1),
        "recall_at_3": avg(r3),
        "recall_at_5": avg(r5),
        "recall_at_10": avg(r10),
        "precision_at_3": avg(p3),
        "precision_at_5": avg(p5),
        "precision_at_10": avg(p10),
        "hit_rate": avg(hits),
        "mrr": avg(rr_scores),
    }
