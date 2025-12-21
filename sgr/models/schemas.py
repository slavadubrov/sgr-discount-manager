from pydantic import BaseModel, Field
from typing import Literal, Union


# --- Phase 1: Routing (Routing Pattern) ---
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


# --- Phase 2: Pricing Logic (The Fuzzy Logic CPU) ---
class PricingLogic(BaseModel):
    """
    Strict reasoning topology for dynamic pricing.
    """

    # 1. Data Analysis (Reflection)
    churn_analysis: str = Field(
        ..., description="Analyze churn_probability (High > 0.7)."
    )
    financial_analysis: str = Field(
        ..., description="Analyze cart_value and profit_margin."
    )

    # 2. Hard Math Enforcement (Constraint Enforcement)
    # The model must output the math equation strings here
    margin_math: str = Field(
        ..., description="Calculate absolute profit: 'Cart $200 * 0.20 Margin = $40'."
    )

    # 3. The Decision Constraint
    max_discount_percent: float = Field(
        ..., description="Max allowed discount % based on margin. NEVER exceed margin."
    )

    # 4. Final Output
    offer_code: str = Field(..., description="Generated code (e.g. SAVE20).")
    customer_message: str = Field(..., description="The final polite offer text.")
