"""Pricing negotiation agent using Schema-Guided Responses.

This module implements the main pricing agent that orchestrates:
1. Intent routing (pricing vs general queries)
2. User context retrieval from hybrid feature store
3. LLM-powered pricing decisions with schema enforcement

The agent follows Single Responsibility Principle - it only handles
the workflow orchestration, delegating specific tasks to specialized modules.
"""

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


def pricing_agent(user_query: str, user_id: str) -> str:
    """Process a user pricing query and return an appropriate response.

    This is the main entry point for the pricing negotiation system.
    It routes queries, fetches user context, and generates personalized
    discount offers based on business rules.

    Args:
        user_query: The user's message/request.
        user_id: Unique identifier for the user.

    Returns:
        A string response - either a discount offer or general reply.
    """
    # Initialize dependencies (singleton patterns handle efficiency)
    llm = LLMClient()
    feature_store = HybridFeatureStore()

    # Build conversation history
    history = [
        {"role": "system", "content": build_routing_prompt(user_id)},
        {"role": "user", "content": user_query},
    ]

    # --- Phase 1: Routing ---
    print(f"\n🤖 Processing: '{user_query}' for {user_id}")
    decision = llm.run_sgr(history, RouterSchema)
    print(f"   📍 Routing decision: {decision.action.tool_name}")

    if decision.action.tool_name == "respond":
        return decision.action.content

    # --- Phase 2: Context Retrieval ---
    if decision.action.tool_name == "fetch_user_features":
        print(f"   🔍 fetching features for {user_id}...")
        context = feature_store.get_user_context(user_id)

        if not context:
            return "Error: User profile not found."

        print(
            f"      [Data] LTV: ${context.get('user_ltv')} (DuckDB) | "
            f"Margin: {context.get('cart_profit_margin', 0) * 100}% (SQLite)"
        )

        # Extract values with defaults
        churn_prob = context.get("churn_probability", DEFAULT_CHURN_PROBABILITY)
        cart_val = context.get("current_cart_value", DEFAULT_CART_VALUE)
        margin = context.get("cart_profit_margin", DEFAULT_PROFIT_MARGIN)
        user_ltv = context.get("user_ltv", 0)

        # Inject context into conversation
        history.append({"role": "assistant", "content": ASSISTANT_FETCH_MESSAGE})
        history.append(
            {
                "role": "user",
                "content": build_pricing_context_prompt(
                    churn_prob=churn_prob,
                    cart_val=cart_val,
                    margin=margin,
                    user_ltv=user_ltv,
                ),
            }
        )

        # --- Phase 3: SGR Logic Execution ---
        print("   🧠 Calculating Offer (Schema Enforced)...")
        offer = llm.run_sgr(history, PricingLogic)

        # Audit Log (The SGR Benefit: explicit reasoning traces)
        print(f"      [Audit] Math: {offer.margin_math}")
        print(f"      [Audit] Max Allowed: {offer.max_discount_percent}%")

        return offer.customer_message

    # Fallback for unknown tool names
    return "I'm sorry, I couldn't process your request."


# --- Run Demo ---
if __name__ == "__main__":
    # Test with a user from our dummy generation script
    # user_102 typically gets random values
    # We need to wrap in try/except because we likely don't have vLLM running
    try:
        response = pricing_agent("I want a discount or I am leaving!", "user_102")
        print(f"\n💬 Final Reply: {response}")
    except Exception as e:
        print(f"\n❌ Execution Error (Expected if vLLM not running): {e}")
        print("Detailed traceback logic would go here.")
