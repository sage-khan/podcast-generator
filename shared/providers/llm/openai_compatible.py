"""One adapter for every provider that speaks the OpenAI chat-completions
REST shape: OpenAI itself, OpenRouter, Groq, xAI (Grok), and the
OpenAI-compatible servers exposed by Ollama and vLLM for local inference.

Only base_url / api_key / default_model differ between them, so a single
class covers six of the eight LLM providers this project supports instead
of one bespoke client per vendor.
"""

from typing import Any, Dict, List, Optional

import requests

from .base import LLMProvider, Message, _normalize_messages


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: str = "",
        extra_headers: Optional[Dict[str, str]] = None,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.extra_headers = extra_headers or {}
        self.timeout = timeout

    def chat(self, messages: List[Message], *, model: str = None, **kwargs: Any) -> str:
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model or self.default_model,
            "messages": _normalize_messages(messages),
            **kwargs,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
