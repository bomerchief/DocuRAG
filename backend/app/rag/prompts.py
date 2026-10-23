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

    "v3": """You are a knowledgeable assistant with access to both uploaded documents and real-time web information.

DOCUMENT CONTEXT:
{doc_context}

WEB SEARCH RESULTS:
{web_context}

QUESTION: {question}

INSTRUCTIONS:
- Combine information from both document context and web search results to give the best answer.
- Prefer document context when it directly answers the question.
- Use web results to supplement, add recency, or fill gaps not covered by documents.
- Cite document sources as [Document Name, Page X].
- Cite web sources as [Web: URL].
- If neither source has relevant information, say so honestly.
- Be clear, concise, and factual.

ANSWER:""",
}


def get_prompt(version: str = "v1") -> str:
    return PROMPTS.get(version, PROMPTS["v1"])


def build_context_string(chunks: list) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Source {i}: {chunk.document_name}, Page {chunk.page}]"
        parts.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def build_web_context_string(web_results: list) -> str:
    if not web_results:
        return "No web results available."
    parts = []
    for i, r in enumerate(web_results, 1):
        parts.append(f"[Web {i}: {r.title}]\nURL: {r.url}\n{r.content}")
    return "\n\n---\n\n".join(parts)


def format_prompt(question: str, chunks: list, version: str = "v1", web_results: list = None) -> str:
    template = get_prompt(version)
    if version == "v3":
        doc_context = build_context_string(chunks) if chunks else "No document context available."
        web_context = build_web_context_string(web_results or [])
        return template.format(doc_context=doc_context, web_context=web_context, question=question)
    context = build_context_string(chunks)
    return template.format(context=context, question=question)
