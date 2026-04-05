"""LLM provider abstraction with factory method — Claude, OpenAI, Ollama."""

from __future__ import annotations

from abc import ABC, abstractmethod

from kb.config import Config


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        """Send a prompt and return the completion text."""

    @staticmethod
    def create(config: Config) -> LLMProvider:
        """Factory: create the appropriate provider from config."""
        provider = config.llm_provider.lower()
        if provider == "claude":
            return ClaudeProvider(api_key=config.anthropic_api_key, model=config.llm_model)
        elif provider == "openai":
            return OpenAIProvider(api_key=config.openai_api_key, model=config.llm_model)
        elif provider == "ollama":
            return OllamaProvider(model=config.llm_model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")


class ClaudeProvider(LLMProvider):
    """Anthropic Claude via the anthropic SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the Claude provider")
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIProvider(LLMProvider):
    """OpenAI GPT via the openai SDK."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        import openai

        client = openai.OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


class OllamaProvider(LLMProvider):
    """Ollama local LLM via HTTP API."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        import httpx

        resp = httpx.post(
            f"{self._base_url}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
