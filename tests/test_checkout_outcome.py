"""place_order() sends a checkout_id, and when no answer comes back (or another
request is still taking payment for the cart) it says so with that ID, for
get_status() to tell how the checkout ended."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

import pytest

from cocart import CheckoutOutcomeUnknownException, CheckoutResult, CoCart, Response
from cocart.exceptions import CoCartException, ValidationException
from cocart.http.http_response import HttpResponse

ORDER: Dict[str, Any] = {"payment_method": "cod", "billing_address": {"email": "jane@example.com"}}

ORDER_PLACED: Dict[str, Any] = {
    "object": "order",
    "result": {"code": "order_placed", "message": "Thank you.", "action": None, "redirect_url": None, "error": None},
    "id": 217,
    "number": "217",
    "key": "wc_order_abc",
    "status": {"code": "processing", "label": "Processing"},
}

PAYMENT_IN_PROGRESS: Dict[str, Any] = {
    "code": "cocart_payment_in_progress",
    "message": "This order is already being placed. Check the order before trying again.",
    "data": {"status": 409},
}


class QueueAdapter:
    """Answers each request from a queue: a status code, or an error to raise.
    Keeps the bodies it was sent."""

    def __init__(self, answers: List[Union[int, CoCartException]]) -> None:
        self.answers = answers
        self.sent: List[Optional[Dict[str, Any]]] = []

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        self.sent.append(json.loads(body) if body else None)
        answer = self.answers.pop(0)
        if isinstance(answer, CoCartException):
            raise answer
        if answer == 504:
            return HttpResponse(504, {}, "<html>Gateway Time-out</html>")
        if answer == 409:
            return HttpResponse(409, {}, json.dumps(PAYMENT_IN_PROGRESS))
        if answer >= 400:
            return HttpResponse(answer, {}, '{"code": "cocart_cant_checkout_empty_cart", "message": "Cannot checkout with empty cart.", "data": {"status": 400}}')
        return HttpResponse(answer, {}, json.dumps(ORDER_PLACED))


def client(adapter: QueueAdapter) -> CoCart:
    cocart = CoCart("https://store.com")
    cocart._http_adapter = adapter  # type: ignore[assignment]
    return cocart


def test_each_order_is_sent_with_a_new_random_checkout_id() -> None:
    adapter = QueueAdapter([200, 200])
    checkout = client(adapter).checkout()

    checkout.place_order(ORDER)
    checkout.place_order(ORDER)

    first = adapter.sent[0]["checkout_id"]  # type: ignore[index]
    second = adapter.sent[1]["checkout_id"]  # type: ignore[index]
    assert re.fullmatch(r"chk_[0-9a-f]{32}", first)
    assert re.fullmatch(r"chk_[0-9a-f]{32}", second)
    assert first != second


def test_the_checkout_id_given_is_sent() -> None:
    adapter = QueueAdapter([200])

    client(adapter).checkout().place_order({**ORDER, "checkout_id": "chk_mine_00000000001"})

    assert adapter.sent[0]["checkout_id"] == "chk_mine_00000000001"  # type: ignore[index]


@pytest.mark.parametrize(
    "answer",
    [
        CoCartException("Request timed out.", http_code=0, error_code="request_timeout"),
        CoCartException("Connection refused", http_code=0, error_code="network_error"),
        504,
    ],
    ids=["timeout", "dropped connection", "proxy gave up"],
)
def test_no_answer_says_the_outcome_is_unknown_with_the_checkout_id(answer: Union[int, CoCartException]) -> None:
    adapter = QueueAdapter([answer])

    with pytest.raises(CheckoutOutcomeUnknownException) as caught:
        client(adapter).checkout().place_order(ORDER)

    assert caught.value.checkout_id == adapter.sent[0]["checkout_id"]  # type: ignore[index]
    assert isinstance(caught.value, CoCartException)
    assert len(adapter.sent) == 1


def test_an_error_the_store_answered_with_is_kept() -> None:
    adapter = QueueAdapter([400])

    with pytest.raises(CoCartException) as caught:
        client(adapter).checkout().place_order(ORDER)

    assert not isinstance(caught.value, CheckoutOutcomeUnknownException)
    assert caught.value.error_code == "cocart_cant_checkout_empty_cart"


def test_another_request_taking_payment_says_the_outcome_is_unknown() -> None:
    adapter = QueueAdapter([409])

    with pytest.raises(CheckoutOutcomeUnknownException) as caught:
        client(adapter).checkout().place_order(ORDER)

    assert caught.value.error_code == "cocart_payment_in_progress"
    assert caught.value.http_code == 409
    assert caught.value.checkout_id == adapter.sent[0]["checkout_id"]  # type: ignore[index]


def test_paying_while_another_payment_runs_is_an_ordinary_error() -> None:
    adapter = QueueAdapter([409])

    with pytest.raises(CoCartException) as caught:
        client(adapter).checkout().pay_for_order(217, "wc_order_abc", {"payment_method": "stripe"})

    assert not isinstance(caught.value, CheckoutOutcomeUnknownException)
    assert caught.value.error_code == "cocart_payment_in_progress"


@pytest.mark.parametrize(
    "checkout_id",
    ["too short", "chk_" + "a" * 61, "chk_has spaces_00000", "chk_0000000000000001\n", 1234567890123456789],
    ids=["short", "long", "spaces", "trailing newline", "not a string"],
)
def test_a_checkout_id_the_store_would_refuse_is_refused_before_sending(checkout_id: Any) -> None:
    adapter = QueueAdapter([])

    with pytest.raises(ValidationException) as caught:
        client(adapter).checkout().place_order({**ORDER, "checkout_id": checkout_id})

    assert caught.value.error_code == "checkout_invalid_checkout_id"
    assert adapter.sent == []


def test_the_order_key_is_sent_in_the_body_only_when_paying() -> None:
    adapter = QueueAdapter([200])

    result = client(adapter).checkout().pay_for_order(217, "wc_order_abc", {"payment_method": "cod"})

    assert adapter.sent[0] == {"payment_method": "cod", "order_key": "wc_order_abc"}
    assert result.is_complete()


def test_a_result_without_a_code_is_never_complete() -> None:
    result = CheckoutResult.from_response(Response(200, {}, json.dumps({"object": "order", "id": 5})))

    assert result.code == "payment_failed"
    assert result.is_failed()
    assert not result.is_complete()


def test_printing_a_result_hides_the_client_secret_and_the_order_key() -> None:
    body = {
        **ORDER_PLACED,
        "result": {
            "code": "action_required",
            "message": "Confirm the payment.",
            "action": {
                "type": "stripe_confirm_payment",
                "data": {"client_secret": "pi_123_secret_456", "intent_type": "payment_intent"},
            },
            "redirect_url": None,
            "error": None,
        },
    }
    result = CheckoutResult.from_response(Response(200, {}, json.dumps(body)))

    assert result.needs_confirmation()
    assert result.client_secret == "pi_123_secret_456"
    assert result.order_key == "wc_order_abc"
    for text in (repr(result), str(result)):
        assert "pi_123_secret_456" not in text
        assert "wc_order_abc" not in text
        assert "action_required" in text
