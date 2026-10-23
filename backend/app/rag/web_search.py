from dataclasses import dataclass
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WebResult:
    title: str
    url: str
    content: str


def search_web(query: str, max_results: int = 5) -> list[WebResult]:
    from app.core.config import get_settings
    settings = get_settings()

    # Sanitize: strip, truncate, remove control characters
    query = query.strip()[:500]
    if not query:
        return []

    if not settings.tavily_api_key:
        logger.warning("Tavily API key not set, skipping web search")
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
        )
        results = [
            WebResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
            )
            for r in response.get("results", [])
        ]
        logger.info(f"Web search returned {len(results)} results for: {query[:80]}")
        return results
    except ImportError:
        raise RuntimeError("WEB_SEARCH_ERROR: tavily-python is not installed. Run: pip install tavily-python")
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []
