from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class EvalQuestion:
    question: str
    expected_answer: str
    relevant_chunk_ids: list[str]
    document_name: Optional[str] = None
    page: Optional[int] = None
    category: str = "factual"
    difficulty: str = "medium"


def load_dataset(path: str) -> list[EvalQuestion]:
    resolved = Path(path).resolve()
    allowed = Path("evaluation_sets").resolve()
    if not str(resolved).startswith(str(allowed)):
        raise ValueError(f"Dataset path '{path}' is outside the allowed evaluation_sets directory")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return [EvalQuestion(**item) for item in data]
