"""Pricing agent using Schema-Guided Reasoning (SGR).

The agent routes the request, fetches data for the authenticated caller, asks
the model for a schema-constrained proposal, and approves the discount in
application code. The model never sets the final discount.
"""

from decimal import ROUND_DOWN, Decimal

from .config.constants import (
    DEFAULT_CART_VALUE,
    DEFAULT_CHURN_PROBABILITY,
    DEFAULT_PROFIT_MARGIN,
)
from .models.schemas import PricingLogic, RouterSchema
from .prompts.pricing import ASSISTANT_FETCH_MESSAGE, build_pricing_context_prompt
from .prompts.routing import build_routing_prompt
from .store.hybrid_store import HybridFeatureStore
from .utils.llm_client import LLMClient

MAX_DISCOUNT_PERCENT = Decimal("20")
"""Policy limit for any approved discount, in percentage points."""


def approve_discount(offer: PricingLogic, context: dict) -> Decimal:
    """Enforce the pricing policy independently of the model's explanation."""
    cart_value = Decimal(str(context["current_cart_value"]))
    margin = Decimal(str(context["cart_profit_margin"]))
    proposed = Decimal(str(offer.max_discount_percent))

    if not all(value.is_finite() for value in (cart_value, margin, proposed)):
        raise ValueError("Pricing values must be finite")
    if cart_value <= 0 or not Decimal("0") <= margin <= Decimal("1"):
        raise ValueError("Invalid pricing context")

    if not Decimal("0") <= proposed <= MAX_DISCOUNT_PERCENT:
        raise ValueError("Proposed discount violates pricing policy")
    # Policy rounds down to hundredths of a percentage point before approval.
    approved = proposed.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    gross_profit = cart_value * margin
    discount_cost = cart_value * approved / Decimal("100")
    policy_cap = min(margin * Decimal("100"), MAX_DISCOUNT_PERCENT)
    if not Decimal("0") <= approved <= policy_cap or discount_cost > gross_profit:
        raise ValueError("Proposed discount violates pricing policy")

    return approved


def pricing_agent(user_query: str, user_id: str) -> str:
    """Integrate routing, context, and pricing; user_id is caller-authenticated."""
    llm = LLMClient()
    feature_store = HybridFeatureStore()

    # Build conversation history
    history = [
        {"role": "system", "content": build_routing_prompt(user_id)},
        {"role": "user", "content": user_query},
    ]

    # --- Phase 1: Routing (Uses RouterSchema) ---
    print(f"🤖 Processing: '{user_query}' for {user_id}")
    decision = llm.run_sgr(history, RouterSchema)
    print(f"📍 Routing decision: {decision.action.tool_name}")

    if decision.action.tool_name == "respond":
        return decision.action.content

    # --- Phase 2: Context Retrieval ---
    if decision.action.tool_name == "fetch_user_features":
        # Use the authenticated user_id, never the ID proposed by the model.
        print(f"🔍 Fetching features for {user_id}...")
        context = feature_store.get_user_context(user_id)

        if not context:
            return "Error: User profile not found."

        print(
            f"   [Data] LTV: ${context.get('user_ltv')} | "
            f"Margin: {context.get('cart_profit_margin', 0) * 100}%"
        )

        # Inject context into conversation
        history.append({"role": "assistant", "content": ASSISTANT_FETCH_MESSAGE})
        history.append(
            {
                "role": "user",
                "content": build_pricing_context_prompt(
                    churn_prob=context.get(
                        "churn_probability", DEFAULT_CHURN_PROBABILITY
                    ),
                    cart_val=context.get("current_cart_value", DEFAULT_CART_VALUE),
                    margin=context.get("cart_profit_margin", DEFAULT_PROFIT_MARGIN),
                    user_ltv=context.get("user_ltv", 0),
                ),
            }
        )

        # --- Phase 3: model proposal, then deterministic policy enforcement ---
        print("🧠 Proposing Offer (Schema Enforced)...")
        offer = llm.run_sgr(history, PricingLogic)
        try:
            approved_discount = approve_discount(offer, context)
        except ValueError:
            return "No discount approved: the proposal failed the pricing policy."

        # Audit log: reasoning is inspectable; pricing is application-enforced.
        print(f"   [Audit] Math: {offer.margin_math}")
        print(f"   [Audit] Approved Discount: {approved_discount}%")

        return (
            f"Illustrative approved discount: {approved_discount}%. "
            "No coupon has been issued."
        )

    return "I'm sorry, I couldn't process your request."


if __name__ == "__main__":
    response = pricing_agent("I want a discount or I'm leaving!", "user_102")
    print(f"\n💬 Final Reply: {response}")
