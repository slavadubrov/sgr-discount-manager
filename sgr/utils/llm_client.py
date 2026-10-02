"""LLM client for schema-constrained generation with vLLM.

vLLM's structured outputs constrain the JSON shape during generation. The
backend (for example XGrammar) is set on the server with
`--structured-outputs-config.backend`. The application still checks that the
completion finished, validates it with Pydantic, and enforces the discount
policy in `sgr.agent.approve_discount`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeVar

from openai import OpenAI

from ..config.constants import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_KEY,
    DEFAULT_TEMPERATURE,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")


def completed_content(completion) -> str:
    """Reject incomplete, refused, or empty results before JSON validation."""
    if not completion.choices:
        raise ValueError("No completion returned")
    choice = completion.choices[0]
    if choice.finish_reason != "stop" or getattr(choice.message, "refusal", None):
        raise ValueError("Completion was not successful")
    content = choice.message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Completion has no content")
    return content


class LLMClient:
    """Wrapper for an OpenAI-compatible vLLM server with structured outputs.

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
        """Reuse one client per process."""
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
            base_url: API base URL. Defaults to a local vLLM server.
            api_key: API key. Local vLLM commonly has no authentication;
                "EMPTY" is not authentication.
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
        """Auto-detect the model running on the vLLM server."""
        models = self.client.models.list()
        if not models.data:
            raise RuntimeError("vLLM reported no available models")
        return models.data[0].id

    def run_sgr(self, messages: list[dict], schema_class: type[T]) -> T:
        """Run inference with Schema-Guided Reasoning constraints.

        Uses vLLM structured outputs to constrain the JSON shape at generation
        time, then checks completion and validates the result with Pydantic.

        Raises:
            ValueError: If the completion is incomplete, refused, or empty.
            ValidationError: If the response does not match the schema.
        """
        schema_dict = schema_class.model_json_schema()

        # Add the schema to the system message for prompt guidance
        enhanced_messages = messages.copy()
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            schema_json = json.dumps(schema_dict, indent=2)
            enhanced_messages[0] = {
                "role": "system",
                "content": (
                    enhanced_messages[0]["content"]
                    + f"\n\nRespond with JSON matching this schema:\n{schema_json}"
                ),
            }

        # vLLM v0.12+ structured outputs. Configure the backend on the server.
        # See: https://docs.vllm.ai/en/latest/features/structured_outputs/
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=enhanced_messages,
            temperature=DEFAULT_TEMPERATURE,
            extra_body={"structured_outputs": {"json": schema_dict}},
        )

        return schema_class.model_validate_json(completed_content(completion))
