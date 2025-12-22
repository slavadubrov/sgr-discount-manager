"""Entry point for the SGR Discount Manager.

This module provides a simple CLI interface for running the pricing agent.
"""

from sgr import pricing_agent


def main() -> None:
    """Run the pricing agent demo."""
    print("SGR Discount Manager - AI-powered pricing negotiation\n")

    try:
        response = pricing_agent("I want a discount or I am leaving!", "user_102")
        print(f"\n💬 Final Reply: {response}")
    except Exception as e:
        print(f"\n❌ Execution Error (Expected if vLLM not running): {e}")
        print("Start vLLM server with a supported model to test the full flow.")


if __name__ == "__main__":
    main()
