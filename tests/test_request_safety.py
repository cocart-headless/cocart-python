from __future__ import annotations

from typing import Dict, Optional

import pytest

from cocart import CoCart
from cocart.exceptions import CoCartException
from cocart.http.http_response import HttpResponse
from cocart.http.requests_adapter import RequestsAdapter
from cocart.http.safe_error_message import safe_error_message
from tests.mock_http_adapter import MockHttpAdapter

SECRETS = ("t_secret_cart_key", "ck_live_secret", "cs_live_secret")


class TestErrorMessages:
    def test_name_the_route_but_never_the_query_string(self) -> None:
        mock_adapter = MockHttpAdapter()
        client = CoCart(
            "https://store.com",
            cart_key="t_secret_cart_key",
            consumer_key="ck_live_secret",
            consumer_secret="cs_live_secret",
        )
        client._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(400, body='{"code": "cocart_coupon_invalid", "message": "Coupon is not valid.", "data": {"status": 400}}')

        with pytest.raises(CoCartException) as exc_info:
            client.cart().apply_coupon("nope")

        message = str(exc_info.value)
        assert message == "POST /cocart/v2/cart/apply-coupon: Coupon is not valid. [cocart_coupon_invalid]"
        assert "store.com" not in message
        for secret in SECRETS:
            assert secret not in message

    def test_keep_a_custom_rest_prefix_out_of_the_route(self) -> None:
        mock_adapter = MockHttpAdapter()
        client = CoCart("https://store.com", rest_prefix="api", cart_key="t_secret_cart_key")
        client._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(404, body='{"code": "cocart_product_not_found", "message": "Product not found."}')

        with pytest.raises(CoCartException) as exc_info:
            client.products().find(99)

        assert str(exc_info.value) == "GET /api/cocart/v2/products/99: Product not found. [cocart_product_not_found]"


class _FailingAdapter:
    """Raises what an HTTP library raises when the store can't be reached."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        raise self.error


class TestConnectionErrors:
    def test_safe_error_message_removes_query_strings(self) -> None:
        assert safe_error_message(
            "HTTPSConnectionPool(host='store.com', port=443): Max retries exceeded with url: "
            "/wp-json/cocart/v2/cart?cart_key=t_secret_cart_key (Caused by NewConnectionError('refused'))"
        ) == (
            "HTTPSConnectionPool(host='store.com', port=443): Max retries exceeded with url: "
            "/wp-json/cocart/v2/cart (Caused by NewConnectionError('refused'))"
        )
        assert safe_error_message(
            "Failed to fetch https://store.com/wp-json/cocart/v2/cart?cart_key=t_secret_cart_key&x=1#frag."
        ) == "Failed to fetch https://store.com/wp-json/cocart/v2/cart"
        assert safe_error_message("Connection refused") == "Connection refused"

    def test_requests_adapter_keeps_the_cart_key_out(self) -> None:
        # Nothing listens on port 1, so requests fails with a ConnectionError naming the URL.
        client = CoCart("http://127.0.0.1:1", cart_key="t_secret_cart_key", timeout=5)
        client._http_adapter = RequestsAdapter()

        with pytest.raises(CoCartException) as exc_info:
            client.cart().get()

        error = exc_info.value
        assert error.error_code == "network_error"
        assert "/wp-json/cocart/v2/cart" in str(error)
        assert "t_secret_cart_key" not in str(error)
        # Not chained: the original exception carries the full URL.
        assert error.__cause__ is None
        assert error.__suppress_context__

    def test_other_adapter_errors_are_wrapped_without_the_query_string(self) -> None:
        client = CoCart("https://store.com", cart_key="t_secret_cart_key")
        client._http_adapter = _FailingAdapter(  # type: ignore[assignment]
            RuntimeError("boom at https://store.com/wp-json/cocart/v2/cart?cart_key=t_secret_cart_key")
        )

        with pytest.raises(CoCartException) as exc_info:
            client.cart().get()

        assert str(exc_info.value) == "boom at https://store.com/wp-json/cocart/v2/cart"
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__


class TestGetCart:
    def test_returns_the_cart_sent_with_cocart_item_not_in_cart(self) -> None:
        cart = {"cart_key": "t_1", "items": [{"item_key": "abc"}], "totals": {"total": "3600"}}
        error = CoCartException(
            "Item specified does not exist in cart.",
            404,
            "cocart_item_not_in_cart",
            {"code": "cocart_item_not_in_cart", "data": {"status": 404, "cart": cart}},
        )
        assert error.get_cart() == cart

    def test_is_none_when_the_error_has_no_cart(self) -> None:
        assert CoCartException("Nope", 404, "cocart_coupon_not_exist", {"data": {"status": 404}}).get_cart() is None
        assert CoCartException("Nope", 404, "x", {"data": {"cart": []}}).get_cart() is None
        assert CoCartException("Nope").get_cart() is None

    def test_from_a_response(self) -> None:
        mock_adapter = MockHttpAdapter()
        client = CoCart("https://store.com")
        client._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(
            404,
            body='{"code": "cocart_item_not_in_cart", "message": "Item specified does not exist in cart.", '
            '"data": {"status": 404, "cart": {"items": [{"item_key": "def"}], "item_count": 1}}}',
        )

        with pytest.raises(CoCartException) as exc_info:
            client.cart().update_item("abc", 2)

        cart = exc_info.value.get_cart()
        assert cart is not None
        assert cart["items"][0]["item_key"] == "def"
