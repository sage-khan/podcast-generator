"""Adapter for Google's Gemini API (generativelanguage.googleapis.com).

Uses the plain REST endpoint rather than the google-generativeai SDK so this
package has no Google-specific dependency — it only needs `requests`, same
as every other adapter here.
"""

from typing import Any, List

import requests

from .base import LLMProvider, Message, _normalize_messages

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, default_model: str = "gemini-2.5-flash", timeout: int = 120):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    # Gemini nests sampling params under generationConfig with its own key
    # names rather than accepting them as top-level request fields.
    _GENERATION_CONFIG_KEYS = {
        "temperature": "temperature",
        "max_tokens": "maxOutputTokens",
        "top_p": "topP",
        "top_k": "topK",
    }

    def chat(self, messages: List[Message], *, model: str = None, **kwargs: Any) -> str:
        normalized = _normalize_messages(messages)
        system_text = "\n".join(m["content"] for m in normalized if m["role"] == "system")
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in normalized
            if m["role"] != "system"
        ]

        generation_config = {}
        remaining_kwargs = {}
        for key, value in kwargs.items():
            if key in self._GENERATION_CONFIG_KEYS:
                generation_config[self._GENERATION_CONFIG_KEYS[key]] = value
            else:
                remaining_kwargs[key] = value

        payload: dict = {"contents": contents, **remaining_kwargs}
        if generation_config:
            payload["generationConfig"] = generation_config
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        model_name = model or self.default_model
        response = requests.post(
            f"{_API_BASE}/{model_name}:generateContent",
            params={"key": self.api_key},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
