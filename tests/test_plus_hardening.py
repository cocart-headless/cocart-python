"""Client hardening for CoCart Plus 2.0: the retry header it sends, debug output
that keeps keys and emails out of logs, an ETag cache that respects
``Cache-Control``, events for ``request_raw()``, and the error mapping."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import pytest

from cocart import CoCart, Response
from cocart.exceptions import AuthenticationException, CoCartException, ValidationException
from tests.mock_http_adapter import MockHttpAdapter


def make_client(adapter: MockHttpAdapter, **kwargs: Any) -> CoCart:
    client = CoCart("https://store.com", **kwargs)
    client._http_adapter = adapter  # type: ignore[assignment]
    return client


def reply(adapter: MockHttpAdapter, status: int, body: Any = None, headers: Dict[str, str] | None = None) -> None:
    adapter.queue(status, headers or {}, json.dumps({} if body is None else body))


@pytest.fixture
def delays(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    slept: List[float] = []
    monkeypatch.setattr("cocart.cocart.time.sleep", slept.append)
    return slept


def test_waits_as_long_as_ratelimit_retry_after_says_before_retrying_a_429(delays: List[float]) -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 429, {"code": "cocart_rate_limited", "message": "Slow down"}, {"RateLimit-Retry-After": "7"})
    reply(adapter, 200, {"items": []})

    make_client(adapter, max_retries=1).cart().get()

    assert delays == [7.0]


def test_still_reads_retry_after_when_that_is_all_a_proxy_sends(delays: List[float]) -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 429, {}, {"Retry-After": "3"})
    reply(adapter, 200, {})

    make_client(adapter, max_retries=1).cart().get()

    assert delays == [3.0]


def test_ratelimit_retry_after_wins_and_the_wait_is_capped_at_a_minute() -> None:
    client = make_client(MockHttpAdapter())

    both = Response(429, {"RateLimit-Retry-After": "4", "Retry-After": "9"}, "{}")
    long = Response(429, {"RateLimit-Retry-After": "600"}, "{}")

    assert client._get_retry_delay(1, both) == 4.0
    assert client._get_retry_delay(1, long) == 60.0


def test_debug_output_hides_every_query_value(caplog: pytest.LogCaptureFixture) -> None:
    adapter = MockHttpAdapter()
    client = make_client(adapter, debug=True)

    with caplog.at_level(logging.DEBUG, logger="cocart"):
        client.get("cart", {"order_key": "wc_order_secret", "email": "jane@example.com"})
        client.request_raw("GET", "cocart/v2/order-received/12", {"order_key": "wc_order_secret", "email": "jane@example.com"})

    output = caplog.text
    assert "order_key=***" in output
    assert "email=***" in output
    assert "wc_order_secret" not in output
    assert "jane@example.com" not in output
    assert "jane%40example.com" not in output


def test_events_keep_the_raw_url() -> None:
    adapter = MockHttpAdapter()
    client = make_client(adapter, debug=True)
    urls: List[str] = []
    client.on("request", lambda data: urls.append(data["url"]))

    client.request_raw("GET", "cocart/v2/order-received/12", {"order_key": "wc_order_secret"})

    assert urls == ["https://store.com/wp-json/cocart/v2/order-received/12?order_key=wc_order_secret"]


def test_does_not_keep_a_no_store_response_in_the_etag_cache() -> None:
    adapter = MockHttpAdapter()
    headers = {"ETag": '"abc"', "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, private"}
    reply(adapter, 200, {"object": "order"}, headers)
    reply(adapter, 200, {"object": "order"}, headers)
    client = make_client(adapter)

    client.get("cart")
    client.get("cart")

    assert "If-None-Match" not in adapter.requests[1]["headers"]  # type: ignore[operator]


def test_does_not_keep_a_private_response_in_the_etag_cache() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 200, {}, {"ETag": '"abc"', "Cache-Control": "private, max-age=60"})
    reply(adapter, 200, {})
    client = make_client(adapter)

    client.get("cart")
    client.get("cart")

    assert "If-None-Match" not in adapter.requests[1]["headers"]  # type: ignore[operator]


def test_still_uses_the_etag_cache_for_a_response_that_may_be_stored() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 200, {"items": []}, {"ETag": '"abc"', "Cache-Control": "public, max-age=60"})
    reply(adapter, 200, {"items": []})
    client = make_client(adapter)

    client.get("products")
    client.get("products")

    assert adapter.requests[1]["headers"]["If-None-Match"] == '"abc"'  # type: ignore[index]


def test_request_raw_emits_request_and_response_events_with_the_response() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 200, {"object": "order", "result": {"code": "order_placed"}})
    client = make_client(adapter)
    seen: List[str] = []
    codes: List[Any] = []
    client.on("request", lambda data: seen.append(f"request {data['method']}"))
    client.on("response", lambda data: (
        seen.append(f"response {data['status']}"),
        codes.append(data["response"].get("result.code")),
    ))

    client.request_raw("POST", "cocart/v2/checkout", data={"payment_method": "cod"})

    assert seen == ["request POST", "response 200"]
    assert codes == ["order_placed"]


def test_request_raw_error_names_its_route_and_emits_an_error_event() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 404, {"code": "cocart_order_not_found", "message": "Not found.", "data": {"status": 404}})
    client = make_client(adapter)
    errors: List[str] = []
    client.on("error", lambda data: errors.append(str(data["error"])))

    with pytest.raises(CoCartException) as caught:
        client.request_raw("GET", "cocart/v2/order-received/12", {"order_key": "wc_order_secret"})

    message = "GET /cocart/v2/order-received/12: Not found. [cocart_order_not_found]"
    assert str(caught.value) == message
    assert errors == [message]


def test_request_raw_is_never_sent_again(delays: List[float]) -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 429, {"code": "cocart_rate_limited", "message": "Slow down"}, {"RateLimit-Retry-After": "1"})
    client = make_client(adapter, max_retries=3)

    with pytest.raises(CoCartException):
        client.request_raw("POST", "cocart/v2/checkout", data={"payment_method": "cod"})

    assert len(adapter.requests) == 1
    assert delays == []


def test_a_409_is_never_a_validation_error_even_when_its_code_says_invalid() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 409, {"code": "cocart_order_invalid_status", "message": "Paid already.", "data": {"status": 409}})

    with pytest.raises(CoCartException) as caught:
        make_client(adapter).request_raw("POST", "cocart/v2/order-received/12/pay")

    assert not isinstance(caught.value, ValidationException)
    assert caught.value.http_code == 409


@pytest.mark.parametrize("status", [429, 500, 503])
def test_a_rate_limit_or_server_error_is_never_a_validation_error(status: int) -> None:
    adapter = MockHttpAdapter()
    reply(adapter, status, {"code": "cocart_missing_something_invalid", "message": "Nope.", "data": {"status": status}})

    with pytest.raises(CoCartException) as caught:
        make_client(adapter).request_raw("GET", "cocart/v2/checkout")

    assert type(caught.value) is CoCartException
    assert caught.value.http_code == status


def test_400_is_still_a_validation_error_and_401_an_authentication_error() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 400, {"code": "cocart_field_required", "message": "Missing.", "data": {"status": 400}})
    reply(adapter, 401, {"code": "cocart_rest_authentication_required", "message": "Log in.", "data": {"status": 401}})
    client = make_client(adapter)

    with pytest.raises(ValidationException):
        client.request_raw("POST", "cocart/v2/checkout")
    with pytest.raises(AuthenticationException):
        client.request_raw("GET", "cocart/v2/my-account")


def test_reads_every_field_at_fault_the_first_one_and_the_reason_from_an_error() -> None:
    adapter = MockHttpAdapter()
    reply(adapter, 400, {
        "code": "cocart_invalid_address_fields",
        "message": "Check the address.",
        "data": {
            "status": 400,
            "field": "billing.postcode",
            "fields": {"billing.postcode": "Enter a valid postcode.", "billing.phone": "Enter a phone number."},
            "reason": "postcode_format",
        },
    })

    with pytest.raises(CoCartException) as caught:
        make_client(adapter).request_raw("PUT", "cocart/v2/checkout")

    assert caught.value.get_fields() == {
        "billing.postcode": "Enter a valid postcode.",
        "billing.phone": "Enter a phone number.",
    }
    assert caught.value.get_field() == "billing.postcode"
    assert caught.value.get_reason() == "postcode_format"


def test_an_error_without_field_details_gives_an_empty_dict_and_nones() -> None:
    error = CoCartException("Nope", 404, "cocart_order_not_found", {"code": "cocart_order_not_found", "data": {"status": 404}})

    assert error.get_fields() == {}
    assert error.get_field() is None
    assert error.get_reason() is None
