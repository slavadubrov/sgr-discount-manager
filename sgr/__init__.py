"""SGR Discount Manager - AI-powered pricing negotiation.

This package provides an LLM-based pricing agent that uses Schema-Guided
Responses (SGR) to make deterministic discount decisions based on user
context from a hybrid feature store.

Example:
    >>> from sgr import pricing_agent
    >>> response = pricing_agent("I want a discount!", "user_102")
"""

from .agent import pricing_agent
from .models.schemas import FeatureLookup, GeneralResponse, PricingLogic, RouterSchema

__all__ = [
    "pricing_agent",
    "RouterSchema",
    "PricingLogic",
    "FeatureLookup",
    "GeneralResponse",
]
