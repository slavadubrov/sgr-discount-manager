from pydantic import BaseModel, Field
from typing import Literal, Union


# --- Phase 1: Routing (Union for branching) ---
class FeatureLookup(BaseModel):
    """Route to DB lookup if pricing context is needed."""

    rationale: str
    tool_name: Literal["fetch_user_features"] = "fetch_user_features"
    user_id: str


class GeneralResponse(BaseModel):
    """Standard response for non-pricing queries."""

    tool_name: Literal["respond"] = "respond"
    content: str


class RouterSchema(BaseModel):
    action: Union[FeatureLookup, GeneralResponse]


# --- Phase 2: Pricing Logic (Cascade for sequential reasoning) ---
class PricingLogic(BaseModel):
    """
    Structured response for dynamic pricing. The fields record an intended analysis→decision flow.
    """

    # 1. Data Analysis (Reflection)
    churn_analysis: str = Field(
        ..., description="Analyze churn_probability (High > 0.7)."
    )
    financial_analysis: str = Field(
        ..., description="Analyze cart_value and profit_margin."
    )

    # 2. Recorded calculation; application code recomputes policy
    margin_math: str = Field(
        ..., description="Calculate absolute profit: 'Cart $200 * 0.20 Margin = $40'."
    )

    # 3. Model-proposed decision; application code approves it.
    max_discount_percent: float = Field(
        ...,
        description="Proposed discount percentage. Application code enforces policy.",
    )
