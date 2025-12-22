"""Prompt templates for the SGR discount manager."""

from .pricing import ASSISTANT_FETCH_MESSAGE, build_pricing_context_prompt
from .routing import build_routing_prompt

__all__ = [
    "build_routing_prompt",
    "build_pricing_context_prompt",
    "ASSISTANT_FETCH_MESSAGE",
]
