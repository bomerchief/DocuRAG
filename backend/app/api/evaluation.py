from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.evaluation import EvaluationRun, EvaluationQuestion
from app.evaluation.dataset import load_dataset, EvalQuestion
from app.evaluation.runner import run_evaluation
from app.utils.hashing import generate_id

router = APIRouter()
settings = get_settings()

EVAL_SETS_DIR = Path("evaluation_sets")

# In-memory progress tracker: run_id -> {current, total, status}
_run_progress: dict[str, dict] = {}


class EvalRunRequest(BaseModel):
    dataset: str = "sample_questions.json"
    document_ids: Optional[list[str]] = None
    top_k: int = 5
    chunk_size: int = 800
    chunk_overlap: int = 100
    similarity_threshold: float = 0.5
    prompt_version: str = "v1"


class EvalRunResponse(BaseModel):
    run_id: str
    status: str
    metrics: Optional[dict] = None


def _run_evaluation_task(run_id: str, request: EvalRunRequest):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        dataset_path = (EVAL_SETS_DIR / request.dataset).resolve()
        if not str(dataset_path).startswith(str(EVAL_SETS_DIR.resolve())):
            raise ValueError("Dataset path is outside the allowed directory")
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {request.dataset}")

        questions = load_dataset(str(dataset_path))
        _run_progress[run_id] = {"current": 0, "total": len(questions), "status": "running"}

        metrics = run_evaluation(
            questions=questions,
            document_ids=request.document_ids,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            prompt_version=request.prompt_version,
            progress_tracker=_run_progress[run_id],
        )

        run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if run:
            for key, val in metrics.items():
                if key != "question_results" and hasattr(run, key):
                    setattr(run, key, val)
            run.question_results = metrics.get("question_results", [])
            run.num_questions = metrics["num_questions"]

            # Save per-question records
            for qr in metrics.get("question_results", []):
                eq = EvaluationQuestion(
                    id=generate_id(),
                    run_id=run_id,
                    question=qr["question"],
                    expected_answer=qr.get("expected_answer"),
                    generated_answer=qr.get("generated_answer"),
                    relevant_chunk_ids=qr.get("relevant_chunk_ids"),
                    retrieved_chunk_ids=qr.get("retrieved_chunk_ids"),
                    retrieved_scores=qr.get("retrieved_scores"),
                    recall_at_k=qr.get("recall_at_k"),
                    precision_at_k=qr.get("precision_at_k"),
                    reciprocal_rank=qr.get("reciprocal_rank"),
                    hit=qr.get("hit"),
                    faithfulness=qr.get("faithfulness"),
                    answer_correctness=qr.get("answer_correctness"),
                    hallucination_label=qr.get("hallucination_label"),
                    retrieval_latency_ms=qr.get("retrieval_latency_ms"),
                    generation_latency_ms=qr.get("generation_latency_ms"),
                    total_latency_ms=qr.get("total_latency_ms"),
                    category=qr.get("category"),
                    difficulty=qr.get("difficulty"),
                )
                db.add(eq)

            run.dataset_name = request.dataset
            db.commit()
        _run_progress[run_id]["status"] = "completed"
    except Exception as e:
        run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if run:
            run.dataset_name = f"ERROR: {e}"
            db.commit()
        if run_id in _run_progress:
            _run_progress[run_id]["status"] = f"error: {e}"
    finally:
        db.close()


@router.post("/evaluation/run", response_model=EvalRunResponse)
def start_evaluation_run(
    request: EvalRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run_id = generate_id()
    run = EvaluationRun(
        id=run_id,
        dataset_name=request.dataset,
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
        prompt_version=request.prompt_version,
        num_questions=0,
    )
    db.add(run)
    db.commit()

    background_tasks.add_task(_run_evaluation_task, run_id, request)
    return EvalRunResponse(run_id=run_id, status="running")


@router.get("/evaluation/runs")
def list_evaluation_runs(db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "dataset_name": r.dataset_name,
            "embedding_model": r.embedding_model,
            "llm_model": r.llm_model,
            "chunk_size": r.chunk_size,
            "chunk_overlap": r.chunk_overlap,
            "top_k": r.top_k,
            "similarity_threshold": r.similarity_threshold,
            "prompt_version": r.prompt_version,
            "num_questions": r.num_questions,
            "recall_at_5": r.recall_at_5,
            "precision_at_5": r.precision_at_5,
            "mrr": r.mrr,
            "faithfulness": r.faithfulness,
            "answer_correctness": r.answer_correctness,
            "hallucination_rate": r.hallucination_rate,
            "avg_latency_ms": r.avg_latency_ms,
            "created_at": str(r.created_at),
        }
        for r in runs
    ]


@router.get("/evaluation/runs/{run_id}")
def get_evaluation_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Evaluation run not found")
    questions = db.query(EvaluationQuestion).filter(EvaluationQuestion.run_id == run_id).all()
    return {
        "id": run.id,
        "dataset_name": run.dataset_name,
        "config": {
            "embedding_model": run.embedding_model,
            "llm_model": run.llm_model,
            "chunk_size": run.chunk_size,
            "chunk_overlap": run.chunk_overlap,
            "top_k": run.top_k,
            "similarity_threshold": run.similarity_threshold,
            "prompt_version": run.prompt_version,
        },
        "metrics": {
            "recall_at_1": run.recall_at_1,
            "recall_at_3": run.recall_at_3,
            "recall_at_5": run.recall_at_5,
            "recall_at_10": run.recall_at_10,
            "precision_at_3": run.precision_at_3,
            "precision_at_5": run.precision_at_5,
            "precision_at_10": run.precision_at_10,
            "hit_rate": run.hit_rate,
            "mrr": run.mrr,
            "answer_correctness": run.answer_correctness,
            "faithfulness": run.faithfulness,
            "context_relevance": run.context_relevance,
            "answer_relevance": run.answer_relevance,
            "hallucination_rate": run.hallucination_rate,
            "avg_latency_ms": run.avg_latency_ms,
            "p50_latency_ms": run.p50_latency_ms,
            "p95_latency_ms": run.p95_latency_ms,
        },
        "num_questions": run.num_questions,
        "created_at": str(run.created_at),
        "question_results": [
            {
                "question": q.question,
                "expected_answer": q.expected_answer,
                "generated_answer": q.generated_answer,
                "recall_at_k": q.recall_at_k,
                "precision_at_k": q.precision_at_k,
                "reciprocal_rank": q.reciprocal_rank,
                "hit": q.hit,
                "faithfulness": q.faithfulness,
                "answer_correctness": q.answer_correctness,
                "hallucination_label": q.hallucination_label,
                "retrieval_latency_ms": q.retrieval_latency_ms,
                "generation_latency_ms": q.generation_latency_ms,
                "total_latency_ms": q.total_latency_ms,
                "retrieved_chunk_ids": q.retrieved_chunk_ids,
                "retrieved_scores": q.retrieved_scores,
                "category": q.category,
                "difficulty": q.difficulty,
                # context_chunks stored in JSON question_results on the run
                "context_chunks": next(
                    (r.get("context_chunks") for r in (run.question_results or []) if r.get("question") == q.question),
                    None,
                ),
            }
            for q in questions
        ],
    }


@router.get("/evaluation/runs/{run_id}/status")
def get_run_status(run_id: str):
    """Poll progress of a running evaluation."""
    progress = _run_progress.get(run_id)
    if not progress:
        return {"run_id": run_id, "status": "unknown", "current": 0, "total": 0}
    return {"run_id": run_id, **progress}


@router.get("/evaluation/datasets")
def list_datasets():
    if not EVAL_SETS_DIR.exists():
        return []
    return [f.name for f in EVAL_SETS_DIR.glob("*.json")]
