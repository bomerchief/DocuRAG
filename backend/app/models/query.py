from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    document_ids = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    retrieval_latency_ms = Column(Float, nullable=True)
    generation_latency_ms = Column(Float, nullable=True)
    total_latency_ms = Column(Float, nullable=True)
    chunks_retrieved = Column(Integer, nullable=True)
    prompt_size = Column(Integer, nullable=True)
    response_length = Column(Integer, nullable=True)
    top_k = Column(Integer, nullable=True)
    similarity_threshold = Column(Float, nullable=True)
    llm_model = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    status = Column(String, default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
