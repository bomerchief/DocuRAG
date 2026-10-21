from abc import ABC, abstractmethod
from typing import Optional
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        pass


class LocalLLMProvider(LLMProvider):
    """Ollama-backed local LLM."""

    def __init__(self, model: str, base_url: str, timeout: float = 60.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except httpx.ConnectError:
            raise RuntimeError(
                "LLM_UNAVAILABLE: Cannot connect to Ollama. "
                "Please ensure Ollama is running: `ollama serve`"
            )
        except httpx.TimeoutException:
            raise RuntimeError("LLM_TIMEOUT: The LLM took too long to respond.")
        except Exception as e:
            raise RuntimeError(f"LLM_ERROR: {e}")

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False


class GeminiProvider(LLMProvider):
    """Google Gemini API provider using the current google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", timeout: float = 60.0):
        if not api_key:
            raise RuntimeError("LLM_CONFIG_ERROR: Gemini API key is not configured.")
        try:
            from google import genai
            from google.genai import types as genai_types
            self._client = genai.Client(api_key=api_key)
            self._types = genai_types
            self.model_name = model
            self.timeout = timeout
        except ImportError:
            raise RuntimeError(
                "LLM_CONFIG_ERROR: google-genai package is not installed. "
                "Run: pip install google-genai"
            )

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                ),
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if "API_KEY" in err.upper() or "api key" in err.lower():
                raise RuntimeError("LLM_UNAVAILABLE: Gemini API key is invalid or missing.")
            if "quota" in err.lower() or "429" in err:
                raise RuntimeError("LLM_UNAVAILABLE: Gemini API quota exceeded.")
            if "timeout" in err.lower():
                raise RuntimeError("LLM_TIMEOUT: Gemini API took too long to respond.")
            raise RuntimeError("LLM_ERROR: Gemini generation failed.")

    def is_available(self) -> bool:
        try:
            self._client.models.generate_content(
                model=self.model_name,
                contents="ping",
                config=self._types.GenerateContentConfig(max_output_tokens=5),
            )
            return True
        except Exception:
            return False


class OpenAIProvider(LLMProvider):
    """Optional OpenAI provider — requires OPENAI_API_KEY env var."""

    def __init__(self, model: str = "gpt-4o-mini"):
        import openai
        self.client = openai.OpenAI()
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()


_llm_instance: Optional[LLMProvider] = None
_llm_provider_name: Optional[str] = None


def get_llm_provider() -> LLMProvider:
    global _llm_instance, _llm_provider_name
    settings = get_settings()

    # Re-create if provider changed (e.g. during testing)
    if _llm_instance is not None and _llm_provider_name == settings.llm_provider:
        return _llm_instance

    provider = settings.llm_provider.lower()

    if provider == "ollama":
        _llm_instance = LocalLLMProvider(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
        )
    elif provider == "gemini":
        _llm_instance = GeminiProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_model,
        )
    elif provider == "openai":
        _llm_instance = OpenAIProvider(model=settings.llm_model)
    else:
        raise RuntimeError(
            f"LLM_CONFIG_ERROR: Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
            "Supported values: ollama, gemini, openai"
        )

    _llm_provider_name = settings.llm_provider
    logger.info(f"LLM provider initialised: {provider} / {settings.llm_model if provider != 'gemini' else settings.gemini_model}")
    return _llm_instance
