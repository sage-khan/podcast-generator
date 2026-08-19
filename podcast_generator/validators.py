from __future__ import annotations

"""Utility helpers for validating and normalising the JSON emitted by the
stand-alone script generators (monologue/dialogue).

We rely on *pydantic* for lightweight, runtime validation.  At runtime this
adds only a few milliseconds but gives us strong guarantees that downstream
Celery tasks receive a well-formed structure and that the ``emotion`` field is
restricted to the allowed set.
"""

from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
    ConfigDict,
)

# Re-export with expected name for downstream imports
ValidationError = PydanticValidationError

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

ALLOWED_EMOTIONS = {
    "auto",
    "neutral",
    "happy",
    "sad",
    "angry",
    "fearful",
    "disgusted",
    "surprised",
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DialogueLine(BaseModel):
    """Single line of dialogue produced by the script generator."""

    speaker: str
    dialogue: Optional[str] = None  # legacy key
    line: Optional[str] = None      # modern key
    # Primary field name is ``emotion``. We still accept legacy ``expression``
    # via a lightweight *model* validator that remaps the key in ``mode='before'``.
    emotion: str = Field(default="neutral")

    # Pydantic v2 config: allow population by field name
    # Strictness: reject unknown keys so typos surface as errors
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    # ---------------------------------------------------------------------
    # Legacy compatibility – remap ``expression`` → ``emotion`` before field
    # validation kicks in.  Using a *model* validator allows us to keep the
    # public schema clean while still supporting older generator scripts.
    # ---------------------------------------------------------------------
    @model_validator(mode="before")
    @classmethod
    def _handle_legacy_expression(cls, data):
        if isinstance(data, dict) and "emotion" not in data and "expression" in data:
            data = {**data, "emotion": data["expression"]}
        return data

    # Normalise/validate emotion -------------------------------------------
    @field_validator("emotion")
    @classmethod
    def _validate_emotion(cls, v):  # noqa: D401 – pydantic validator signature
        if v is None or v == "":
            return "neutral"
        v_lower = str(v).lower()
        if v_lower not in ALLOWED_EMOTIONS:
            raise ValueError(
                f"Emotion '{v}' is not allowed – must be one of {sorted(ALLOWED_EMOTIONS)}"
            )
        return v_lower

    # Convenience accessors -----------------------------------------------
    @property
    def text(self) -> str:
        """Return the dialogue text regardless of legacy vs modern key."""
        return self.dialogue or self.line or ""


class ScriptModel(BaseModel):
    """Top-level JSON object returned by the generator scripts."""

    dialogue: Optional[List[DialogueLine]] = None  # legacy key
    lines: Optional[List[DialogueLine]] = None     # modern key

    @property
    def all_lines(self) -> List[DialogueLine]:
        """Return list of ``DialogueLine`` regardless of key used."""
        return self.dialogue or self.lines or []


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def validate_script_json(data):
    """Validate & normalise the *script* JSON structure.

    Returns
    -------
    List[DialogueLine]
        The list of validated & normalised dialogue lines.

    Raises
    ------
    pydantic.ValidationError
        If the data does not conform to the expected schema.
    """

    # Support callers that pass bare list of dialogue lines
    if isinstance(data, list):
        data = {"lines": data}

    model = ScriptModel.model_validate(data)
    return model.all_lines


__all__ = [
    "ValidationError",
    "validate_script_json",
    "DialogueLine",
    "ALLOWED_EMOTIONS",
    "ValidationError",
]
