import json
from openai import OpenAI
from .models.schemas import RouterSchema, PricingLogic
from .store.hybrid_store import HybridFeatureStore

# 1. Setup Client (vLLM must be running with --guided-decoding-backend xgrammar)
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
feature_store = HybridFeatureStore()


def get_available_model() -> str:
    """Auto-detect the model running on vLLM server."""
    try:
        models = client.models.list()
        if models.data:
            return models.data[0].id
    except Exception:
        pass
    # Fallback to default
    return "Qwen/Qwen2.5-1.5B-Instruct"


MODEL = get_available_model()


def strip_markdown_json(text: str) -> str:
    """Strip markdown code blocks from JSON response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def run_sgr(messages, schema_class):
    """Helper to run inference with SGR constraints."""
    # Inject schema into system prompt for CPU builds without guided decoding
    schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
    enhanced_messages = messages.copy()

    # Enhance system message with schema
    if enhanced_messages and enhanced_messages[0]["role"] == "system":
        enhanced_messages[0] = {
            "role": "system",
            "content": enhanced_messages[0]["content"]
            + f"\n\nYou MUST respond with raw JSON (no markdown) matching this schema:\n{schema_json}",
        }

    completion = client.chat.completions.create(
        model=MODEL,
        messages=enhanced_messages,
        temperature=0.1,
    )

    raw_response = completion.choices[0].message.content
    clean_json = strip_markdown_json(raw_response)
    return schema_class.model_validate_json(clean_json)


def pricing_agent(user_query: str, user_id: str):
    history = [
        {
            "role": "system",
            "content": """You are an automated pricing negotiation agent. You must respond with valid JSON matching the required schema.

ROUTING RULES:
- If the user mentions discounts, pricing, leaving, canceling, or negotiating: use "fetch_user_features" to get their profile
- For general questions unrelated to pricing: use "respond" with a helpful message

The user_id for lookups is: """
            + user_id,
        }
    ]
    history.append({"role": "user", "content": user_query})

    # --- Phase 1: Routing ---
    print(f"\n🤖 Processing: '{user_query}' for {user_id}")
    decision = run_sgr(history, RouterSchema)
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
            f"      [Data] LTV: ${context.get('user_ltv')} (DuckDB) | Margin: {context.get('cart_profit_margin') * 100}% (SQLite)"
        )

        # Inject Data + Business Rules into Context
        # [cite_start]This is the "Context Engineering" part [cite: 46]
        churn_prob = context.get("churn_probability", 0.5)
        cart_val = context.get("cart_value", 100)
        margin = context.get("cart_profit_margin", 0.2)

        history.append(
            {"role": "assistant", "content": "I'll fetch the user's profile now."}
        )
        history.append(
            {
                "role": "user",
                "content": f"""User profile retrieved. Now calculate and respond with a pricing decision.

USER DATA:
- churn_probability: {churn_prob}
- cart_value: ${cart_val}
- profit_margin: {margin * 100}%
- user_ltv: ${context.get("user_ltv", 0)}

BUSINESS RULES:
1. If churn_probability > 0.7: offer up to 50% of profit margin as discount
2. If churn_probability < 0.3: max discount is 5%
3. NEVER exceed the profit margin

Respond with your analysis and offer as JSON.""",
            }
        )

        # --- Phase 3: SGR Logic Execution ---
        print("   🧠 Calculating Offer (Schema Enforced)...")
        offer = run_sgr(history, PricingLogic)

        # Audit Log (The SGR Benefit: explicit reasoning traces)
        print(f"      [Audit] Math: {offer.margin_math}")
        print(f"      [Audit] Max Allowed: {offer.max_discount_percent}%")

        return offer.customer_message


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
