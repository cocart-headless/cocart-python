from __future__ import annotations

import json

import pytest

from cocart import CoCart
from cocart.exceptions import CoCartException
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestAccountProfile:
    def test_get_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"user":{"id":1}}')
        client.account().get_profile()
        assert "cocart/v2/my-account" in mock_adapter.last_request["url"]
        assert mock_adapter.last_request["method"] == "GET"

    def test_update_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"user":{}}')
        client.account().update_profile({"account_email": "new@example.com"})
        assert "cocart/v2/my-account" in mock_adapter.last_request["url"]
        assert mock_adapter.last_request["method"] == "POST"

    def test_change_password_remaps_fields(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="{}")
        client.account().change_password("oldpass", "newpass", "newpass")
        body = json.loads(mock_adapter.last_request["body"])
        assert body["password_current"] == "oldpass"
        assert body["password_1"] == "newpass"
        assert body["password_2"] == "newpass"
        assert "change-password" in mock_adapter.last_request["url"]


class TestAccountOrders:
    def test_get_orders(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"orders":[]}')
        client.account().get_orders({"per_page": "5"})
        assert "cocart/v2/my-account/orders" in mock_adapter.last_request["url"]
        assert "per_page=5" in mock_adapter.last_request["url"]

    def test_get_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"order_id":42}')
        client.account().get_order(42)
        assert "cocart/v2/my-account/orders/42" in mock_adapter.last_request["url"]

    def test_get_guest_order_sends_email(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"order_id":7}')
        client.account().get_guest_order(7, "guest@example.com")
        assert "cocart/v2/my-account/orders/7" in mock_adapter.last_request["url"]
        assert "email=guest%40example.com" in mock_adapter.last_request["url"] or \
               "email=guest@example.com" in mock_adapter.last_request["url"]


class TestAccountDownloads:
    def test_get_order_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.account().get_order_downloads(3)
        assert "cocart/v2/my-account/orders/3/downloads" in mock_adapter.last_request["url"]

    def test_get_guest_order_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.account().get_guest_order_downloads(3, "g@x.com")
        assert "cocart/v2/my-account/orders/3/downloads" in mock_adapter.last_request["url"]
        assert "email=" in mock_adapter.last_request["url"]

    def test_get_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.account().get_downloads()
        assert "cocart/v2/my-account/downloads" in mock_adapter.last_request["url"]


class TestAccountReviews:
    def test_get_reviews(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.account().get_reviews()
        assert "cocart/v2/my-account/reviews" in mock_adapter.last_request["url"]


class TestAccountNoRoute:
    def test_rest_no_route_becomes_plugin_required(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(404, body=json.dumps({
            "code": "rest_no_route",
            "message": "No route was found.",
            "data": {"status": 404},
        }))
        with pytest.raises(CoCartException) as exc_info:
            client.account().get_profile()
        assert exc_info.value.error_code == "cocart_plugin_required"
