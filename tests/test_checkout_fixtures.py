"""Replays the shared checkout fixtures (tests/fixtures/checkout, copied from
cocart-js's packages/checkout/tests/fixtures): the same request/response data
every CoCart SDK runs, so all of them are tested the same way."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlsplit

import pytest

from cocart import CheckoutResult, CoCart, Response
from cocart.exceptions import CheckoutOutcomeUnknownException, CoCartException
from tests.mock_http_adapter import MockHttpAdapter

STORE = "https://example.com/wp-json/"
FIXTURES = sorted((Path(__file__).parent / "fixtures" / "checkout").glob("*.json"))


def _snake(name: str) -> str:
    return re.sub(r"[A-Z]", lambda m: "_" + m.group(0).lower(), name)


def _seen(request: Dict[str, Any]) -> Dict[str, Any]:
    url = str(request["url"])
    assert url.startswith(STORE)
    parts = urlsplit(url)
    return {
        "method": request["method"],
        "path": parts.path[len("/wp-json/"):],
        "query": dict(parse_qsl(parts.query)),
        "body": json.loads(request["body"]) if request["body"] else None,
    }


def _call(client: CoCart, call: Dict[str, Any]) -> Any:
    args: List[Any] = call["args"]
    method = call["method"]

    if call["target"] == "account":
        return getattr(client.account(), _snake(method))(*args)

    checkout = client.checkout()
    if method == "getCheckout":
        return checkout.get(args[0] if args else None)
    if method == "updateCheckout":
        return checkout.update(args[0])
    if method == "getCheckoutConfig":
        return checkout.get_config()
    if method == "getCheckoutStatus":
        return checkout.get_status(args[0])
    if method == "searchAddresses":
        a = args[0]
        return checkout.search_addresses(a["query"], a.get("country"), a.get("type"), a.get("provider"))
    if method == "getAddressDetails":
        return checkout.get_address_details(args[0]["address_id"], args[0]["provider"])
    if method == "confirmReturn":
        options = args[1] if len(args) > 1 else {}
        return checkout.confirm_return(args[0], options.get("orderId"), options.get("orderKey"))
    return getattr(checkout, _snake(method))(*args)


def test_every_fixture_runs() -> None:
    assert len(FIXTURES) == 53


@pytest.mark.parametrize("path", FIXTURES, ids=[p.stem for p in FIXTURES])
def test_fixture(path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    adapter = MockHttpAdapter()
    for exchange in fixture["exchanges"]:
        adapter.queue(exchange["response"]["status"], {}, json.dumps(exchange["response"]["body"]))

    client = CoCart("https://example.com")
    client._http_adapter = adapter  # type: ignore[assignment]

    outcome: Any = None
    error: Optional[CoCartException] = None
    try:
        outcome = _call(client, fixture["call"])
    except CoCartException as e:
        error = e

    assert [_seen(r) for r in adapter.requests] == [e["request"] for e in fixture["exchanges"]]

    expect = fixture["expect"]
    if "error" in expect:
        assert isinstance(error, CoCartException)
        assert error.error_code == expect["error"]["code"]
        # The checkout-outcome-unknown error carries the checkout_id to ask get_status() about.
        if "checkoutId" in expect["error"]:
            assert isinstance(error, CheckoutOutcomeUnknownException)
            assert error.checkout_id == expect["error"]["checkoutId"]
        return
    if error is not None:
        raise error

    if "result" in expect:
        assert isinstance(outcome, CheckoutResult)
        # `null` in a fixture is a field the result leaves out.
        for key, value in expect["result"].items():
            attribute = getattr(outcome, _snake(key))
            actual = attribute() if callable(attribute) else attribute
            assert actual == value, key
    if "value" in expect:
        value = expect["value"]
        if isinstance(value, list):
            assert outcome == [{_snake(k): v for k, v in card.items()} for card in value]
        else:
            assert outcome == {_snake(k): v for k, v in value.items()}
    if "responseBody" in expect:
        response = outcome.response if isinstance(outcome, CheckoutResult) else outcome
        assert isinstance(response, Response)
        assert response.to_dict() == expect["responseBody"]
