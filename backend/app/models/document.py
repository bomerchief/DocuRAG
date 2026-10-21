from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=True, index=True)  # sha256 for dedup
    num_chunks = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing | ready | error
    error_message = Column(Text, nullable=True)
    ingestion_stage = Column(String, nullable=True)   # current stage label
    ingestion_progress = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    chunk_size = Column(Integer, nullable=True)
    chunk_overlap = Column(Integer, nullable=True)
    embedding_model = Column(String, nullable=True)
