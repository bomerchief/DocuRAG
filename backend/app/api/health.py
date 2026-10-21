from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()
    return {"status": "ok", "env": settings.app_env}


@router.get("/health/config")
def config_check():
    settings = get_settings()
    provider = settings.llm_provider.lower()
    model = settings.gemini_model if provider == "gemini" else settings.llm_model
    return {
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": model,
        "top_k": settings.top_k,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "similarity_threshold": settings.similarity_threshold,
        "prompt_version": settings.prompt_version,
    }


@router.get("/health/llm")
def llm_status():
    """Check LLM provider availability. Never exposes API keys."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    model = settings.gemini_model if provider == "gemini" else settings.llm_model

    try:
        from app.rag.generator import get_llm_provider
        llm = get_llm_provider()

        if hasattr(llm, "is_available"):
            available = llm.is_available()
            status = "available" if available else "unavailable"
        else:
            status = "unknown"

        return {
            "llm_provider": provider,
            "llm_model": model,
            "status": status,
            "gemini_key_configured": bool(settings.gemini_api_key) if provider == "gemini" else None,
        }
    except RuntimeError as e:
        msg = str(e)
        # Strip internal details, never expose key
        if "API key" in msg or "api_key" in msg.lower():
            msg = "Gemini API key is not configured."
        return {"llm_provider": provider, "llm_model": model, "status": "error", "detail": msg}
