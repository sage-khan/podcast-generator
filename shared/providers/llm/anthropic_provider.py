"""Adapter for Anthropic's Messages API.

Anthropic uses a distinct request shape (system prompt as a top-level field,
x-api-key header, required max_tokens) so it can't share the OpenAI-compatible
adapter the way OpenAI/OpenRouter/Groq/Grok/Ollama/vLLM do.
"""

from typing import Any, List

import requests

from .base import LLMProvider, Message, _normalize_messages

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-5", timeout: int = 120):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    def chat(self, messages: List[Message], *, model: str = None, max_tokens: int = 4096, **kwargs: Any) -> str:
        normalized = _normalize_messages(messages)
        system_prompt = "\n".join(m["content"] for m in normalized if m["role"] == "system") or None
        turns = [m for m in normalized if m["role"] != "system"]

        payload = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "messages": turns,
            **kwargs,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            _API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": _API_VERSION,
                "content-type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
