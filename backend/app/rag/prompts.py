from typing import Optional

PROMPTS: dict[str, str] = {
    "v1": """You are a precise document question-answering assistant.

RULES:
1. Answer ONLY using the provided context below.
2. If the context does not contain enough information, say exactly:
   "I couldn't find this information in the provided documents."
3. Never invent, guess, or extrapolate facts.
4. Always cite the source document and page number for every claim.
5. If multiple sources support the answer, cite all of them.
6. Be concise and factual.

CONTEXT:
{context}

QUESTION: {question}

ANSWER (with citations):""",

    "v2": """You are a strict document Q&A assistant. Answer only from the context.

Context:
{context}

Question: {question}

Instructions:
- Use only information from the context above.
- Cite sources as [Document Name, Page X].
- If the answer is not in the context, respond: "I couldn't find this information in the provided documents."
- Do not speculate or add external knowledge.

Answer:""",
}


def get_prompt(version: str = "v1") -> str:
    return PROMPTS.get(version, PROMPTS["v1"])


def build_context_string(chunks: list) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Source {i}: {chunk.document_name}, Page {chunk.page}]"
        parts.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def format_prompt(question: str, chunks: list, version: str = "v1") -> str:
    context = build_context_string(chunks)
    template = get_prompt(version)
    return template.format(context=context, question=question)
