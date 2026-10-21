from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String, primary_key=True)
    dataset_name = Column(String, nullable=False)
    embedding_model = Column(String, nullable=False)
    llm_model = Column(String, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    chunk_overlap = Column(Integer, nullable=False)
    top_k = Column(Integer, nullable=False)
    similarity_threshold = Column(Float, nullable=False)
    prompt_version = Column(String, nullable=False)
    num_questions = Column(Integer, nullable=False)
    # Retrieval metrics
    recall_at_1 = Column(Float, nullable=True)
    recall_at_3 = Column(Float, nullable=True)
    recall_at_5 = Column(Float, nullable=True)
    recall_at_10 = Column(Float, nullable=True)
    precision_at_3 = Column(Float, nullable=True)
    precision_at_5 = Column(Float, nullable=True)
    precision_at_10 = Column(Float, nullable=True)
    hit_rate = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    # Generation metrics
    answer_correctness = Column(Float, nullable=True)
    faithfulness = Column(Float, nullable=True)
    context_relevance = Column(Float, nullable=True)
    answer_relevance = Column(Float, nullable=True)
    hallucination_rate = Column(Float, nullable=True)
    # Latency
    avg_latency_ms = Column(Float, nullable=True)
    p50_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    avg_retrieval_latency_ms = Column(Float, nullable=True)
    avg_generation_latency_ms = Column(Float, nullable=True)
    # Per-question results stored as JSON
    question_results = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class EvaluationQuestion(Base):
    __tablename__ = "evaluation_questions"

    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    generated_answer = Column(Text, nullable=True)
    relevant_chunk_ids = Column(JSON, nullable=True)
    retrieved_chunk_ids = Column(JSON, nullable=True)
    retrieved_scores = Column(JSON, nullable=True)
    recall_at_k = Column(Float, nullable=True)
    precision_at_k = Column(Float, nullable=True)
    reciprocal_rank = Column(Float, nullable=True)
    hit = Column(Integer, nullable=True)
    faithfulness = Column(Float, nullable=True)
    answer_correctness = Column(Float, nullable=True)
    hallucination_label = Column(String, nullable=True)
    retrieval_latency_ms = Column(Float, nullable=True)
    generation_latency_ms = Column(Float, nullable=True)
    total_latency_ms = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
