"""Routing agent prompts for intent classification.

This module contains prompts used by the routing phase of the pricing agent
to determine whether to fetch user features or respond directly.
"""

ROUTING_SYSTEM_PROMPT = """You are an automated pricing negotiation agent. You must respond with valid JSON matching the required schema.

ROUTING RULES:
- If the user mentions discounts, pricing, leaving, canceling, or negotiating: use "fetch_user_features" to get their profile
- For general questions unrelated to pricing: use "respond" with a helpful message

The user_id for lookups is: {user_id}"""


def build_routing_prompt(user_id: str) -> str:
    """Build the routing system prompt with user context.

    Args:
        user_id: The user identifier to include in the prompt.

    Returns:
        Formatted system prompt for routing decisions.
    """
    return ROUTING_SYSTEM_PROMPT.format(user_id=user_id)
