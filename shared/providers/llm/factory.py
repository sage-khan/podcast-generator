"""Selects and constructs an LLMProvider from environment variables.

LLM_PROVIDER picks the backend (default: openrouter, matching this
project's existing behavior). LLM_MODEL optionally overrides the provider's
default model — e.g. set LLM_PROVIDER=groq and LLM_MODEL=llama-3.3-70b-versatile
to run a Meta/Llama model through Groq, or LLM_PROVIDER=ollama with no key
for a fully local setup.

Meta/Llama is intentionally not a provider entry here: it isn't a hosted
API of its own — it's a model family reachable *through* groq, openrouter,
ollama, or vllm by setting LLM_MODEL, so it doesn't need a bespoke adapter.
"""

import os
from typing import Optional

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .openai_compatible import OpenAICompatibleProvider

# name -> (default base_url, default model, env var holding the API key or
# None if the backend doesn't require one, e.g. local Ollama/vLLM).
_OPENAI_COMPATIBLE: dict = {
    "openrouter": ("https://openrouter.ai/api/v1", "openai/gpt-4o", "OPENROUTER_API_KEY"),
    "openai": ("https://api.openai.com/v1", "gpt-4o", "OPENAI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "grok": ("https://api.x.ai/v1", "grok-4", "XAI_API_KEY"),
    "ollama": (os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "llama3.1", None),
    "vllm": (os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1"), "", None),
}

SUPPORTED_PROVIDERS = sorted({*_OPENAI_COMPATIBLE, "anthropic", "gemini"})


def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    """Build the configured LLMProvider.

    Raises ValueError with an actionable message if the provider name is
    unknown or its required API key env var isn't set — callers shouldn't
    have to guess why generation failed.
    """
    provider_name = (name or os.environ.get("LLM_PROVIDER", "openrouter")).lower()
    model_override = os.environ.get("LLM_MODEL")

    if provider_name in _OPENAI_COMPATIBLE:
        base_url, default_model, key_env = _OPENAI_COMPATIBLE[provider_name]
        api_key = os.environ.get(key_env) if key_env else None
        if key_env and not api_key:
            raise ValueError(
                f"{key_env} environment variable not set (required for LLM_PROVIDER={provider_name})."
            )
        return OpenAICompatibleProvider(
            base_url=os.environ.get(f"{provider_name.upper()}_BASE_URL", base_url),
            api_key=api_key,
            default_model=model_override or default_model,
        )

    if provider_name == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set (required for LLM_PROVIDER=anthropic).")
        return AnthropicProvider(api_key=api_key, default_model=model_override or "claude-sonnet-4-5")

    if provider_name == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set (required for LLM_PROVIDER=gemini).")
        return GeminiProvider(api_key=api_key, default_model=model_override or "gemini-2.5-flash")

    raise ValueError(f"Unknown LLM_PROVIDER '{provider_name}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}")
