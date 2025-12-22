"""LLM client wrapper for structured generation with vLLM."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeVar

from openai import OpenAI

from ..config.constants import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_KEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
)
from .json_utils import strip_markdown_json

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")


class LLMClient:
    """Wrapper for OpenAI-compatible LLM inference with schema enforcement.

    This client provides structured generation (SGR) capabilities by injecting
    JSON schemas into prompts and validating responses against Pydantic models.

    Attributes:
        client: The underlying OpenAI client instance.
        model: The model ID to use for inference.

    Example:
        >>> from sgr.models.schemas import RouterSchema
        >>> llm = LLMClient()
        >>> messages = [{"role": "user", "content": "Hello"}]
        >>> result = llm.run_sgr(messages, RouterSchema)
    """

    _instance: LLMClient | None = None

    def __new__(
        cls, base_url: str | None = None, api_key: str | None = None
    ) -> LLMClient:
        """Implement singleton pattern for efficient resource usage."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the LLM client.

        Args:
            base_url: API base URL. Defaults to localhost vLLM server.
            api_key: API key. Defaults to "EMPTY" for local vLLM.
        """
        if getattr(self, "_initialized", False):
            return

        self.client = OpenAI(
            base_url=base_url or DEFAULT_API_BASE_URL,
            api_key=api_key or DEFAULT_API_KEY,
        )
        self.model = self._get_available_model()
        self._initialized = True

    def _get_available_model(self) -> str:
        """Auto-detect the model running on vLLM server.

        Returns:
            The ID of the first available model, or DEFAULT_MODEL as fallback.
        """
        try:
            models = self.client.models.list()
            if models.data:
                return models.data[0].id
        except Exception:
            pass
        return DEFAULT_MODEL

    def run_sgr(self, messages: list[dict], schema_class: type[T]) -> T:
        """Run inference with Schema-Guided Response constraints.

        Injects the Pydantic schema into the system prompt and validates
        the response against the schema.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            schema_class: Pydantic model class to validate response against.

        Returns:
            Validated instance of the schema_class.

        Raises:
            ValidationError: If the response doesn't match the schema.
        """
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        enhanced_messages = messages.copy()

        # Enhance system message with schema instruction
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0] = {
                "role": "system",
                "content": (
                    enhanced_messages[0]["content"]
                    + f"\n\nYou MUST respond with raw JSON (no markdown) matching this schema:\n{schema_json}"
                ),
            }

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=enhanced_messages,
            temperature=DEFAULT_TEMPERATURE,
        )

        raw_response = completion.choices[0].message.content
        clean_json = strip_markdown_json(raw_response)
        return schema_class.model_validate_json(clean_json)
