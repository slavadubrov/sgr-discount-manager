"""Pricing decision prompts for discount calculation.

This module contains prompts used by the pricing phase of the agent
to ask the model for a discount proposal. The rules here guide the model;
`sgr.agent.approve_discount` is the rule that the application enforces.
"""

from ..config.constants import HIGH_CHURN_THRESHOLD, LOW_CHURN_THRESHOLD

ASSISTANT_FETCH_MESSAGE = "I'll fetch the user's profile now."
"""Standard assistant message when initiating feature lookup."""

USER_DATA_TEMPLATE = """User profile retrieved. Now calculate and respond with a pricing decision.

USER DATA:
- churn_probability: {churn_prob}
- cart_value: ${cart_val}
- profit_margin: {margin_percent}%
- user_ltv: ${user_ltv}

BUSINESS RULES:
1. Propose a discount between 0 and 20 percent. It must not exceed the profit margin percentage.
2. If churn_probability > {high_churn_threshold}: you may propose up to that limit.
3. If churn_probability < {low_churn_threshold}: propose at most 5 percent.
4. Application code checks the proposal and rejects any discount above the limit in rule 1.

Respond with your analysis and proposed discount as JSON."""


def build_pricing_context_prompt(
    churn_prob: float,
    cart_val: float,
    margin: float,
    user_ltv: float,
) -> str:
    """Build the pricing context prompt with user data.

    Args:
        churn_prob: User's churn probability (0.0-1.0).
        cart_val: Current cart value in dollars.
        margin: Profit margin as decimal (e.g., 0.2 for 20%).
        user_ltv: User's lifetime value in dollars.

    Returns:
        Formatted prompt with user data and business rules.
    """
    return USER_DATA_TEMPLATE.format(
        churn_prob=churn_prob,
        cart_val=cart_val,
        margin_percent=margin * 100,
        user_ltv=user_ltv,
        high_churn_threshold=HIGH_CHURN_THRESHOLD,
        low_churn_threshold=LOW_CHURN_THRESHOLD,
    )
