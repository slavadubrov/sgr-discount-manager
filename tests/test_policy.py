"""Offline checks for the discount policy and the completion check.

These tests need no model and no vLLM server.
"""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from sgr.agent import approve_discount
from sgr.models.schemas import PricingLogic
from sgr.utils.llm_client import completed_content


def discount(proposal, margin="0.2", cart="200"):
    offer = PricingLogic(
        churn_analysis="",
        financial_analysis="",
        margin_math="",
        max_discount_percent=proposal,
    )
    return approve_discount(
        offer, {"current_cart_value": cart, "cart_profit_margin": margin}
    )


def test_approves_proposals_inside_the_policy():
    assert discount("15") == Decimal("15.00")
    assert discount("0") == 0
    assert discount("20") == 20


def test_rounds_down_before_the_margin_check():
    # 12.346 rounds down to 12.34; rounding up to 12.35 would exceed the margin.
    assert discount("12.346", "0.12346") == Decimal("12.34")
    with pytest.raises(ValueError):
        discount("12.35", "0.12346")


@pytest.mark.parametrize(
    "proposal", ["20.01", "-0.001", "NaN", "Infinity", "-Infinity"]
)
def test_rejects_proposals_outside_the_policy(proposal):
    with pytest.raises(ValueError):
        discount(proposal)


@pytest.mark.parametrize("margin", ["NaN", "Infinity", "-Infinity", "-0.1", "1.1"])
def test_rejects_invalid_margin(margin):
    with pytest.raises(ValueError):
        discount("15", margin)


@pytest.mark.parametrize("cart", ["NaN", "Infinity", "-Infinity", "0", "-1"])
def test_rejects_invalid_cart_value(cart):
    with pytest.raises(ValueError):
        discount("15", cart=cart)


def response(reason="stop", content='{"discount": 15}', refusal=None):
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=reason, message=message)]
    )


def test_accepts_a_finished_completion():
    assert json.loads(completed_content(response())) == {"discount": 15}


@pytest.mark.parametrize(
    "completion",
    [
        SimpleNamespace(choices=[]),
        response(reason="length"),
        response(reason="content_filter"),
        response(reason="tool_calls"),
        response(reason=None),
        response(content=None),
        response(content=""),
        response(content="  "),
        response(refusal="Declined"),
    ],
)
def test_rejects_incomplete_refused_or_empty_completions(completion):
    with pytest.raises(ValueError):
        completed_content(completion)


def test_completion_check_does_not_replace_json_validation():
    # A finished completion can still hold malformed JSON; parsing must fail.
    with pytest.raises(json.JSONDecodeError):
        json.loads(completed_content(response(content='{"discount":')))
