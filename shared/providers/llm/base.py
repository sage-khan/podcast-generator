"""Common interface every LLM provider adapter implements.

Deliberately framework-free (no Django imports) so this package can be used
both from Django app code and from the standalone scripts under scripts/,
and can later be lifted out into its own pip-installable package without
any changes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

Message = Union[Dict[str, str], "ChatMessage"]


class ChatMessage:
    __slots__ = ("role", "content")

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def as_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


def _normalize_messages(messages: List[Message]) -> List[Dict[str, str]]:
    return [m.as_dict() if isinstance(m, ChatMessage) else m for m in messages]


class LLMProvider(ABC):
    """Chat-completion interface shared by every backend.

    Callers pass OpenAI-style ``{"role": ..., "content": ...}`` messages and
    get plain completion text back, regardless of which provider or model
    family is actually configured behind LLM_PROVIDER.
    """

    default_model: str = ""

    @abstractmethod
    def chat(self, messages: List[Message], *, model: str = None, **kwargs: Any) -> str:
        """Send a chat completion request and return the assistant's reply text."""
        raise NotImplementedError
