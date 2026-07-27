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
    c = CoCart("https://example.com", username="user", password="pass")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestAccountProfile:
    def test_get_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"first_name": "John"}')
        response = client.account().get_profile()
        assert response.is_successful()
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account")
        assert mock_adapter.last_request["method"] == "GET"

    def test_update_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"success": true}')
        client.account().update_profile({"account_first_name": "Jane"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["account_first_name"] == "Jane"
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account")

    def test_change_password(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"success": true}')
        client.account().change_password("old_pw", "new_pw", "new_pw")
        body = json.loads(mock_adapter.last_request["body"])
        assert body == {
            "password_current": "old_pw",
            "password_1": "new_pw",
            "password_2": "new_pw",
        }
        assert "change-password" in mock_adapter.last_request["url"]


class TestAccountOrders:
    def test_get_orders(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"orders": []}')
        client.account().get_orders({"page": "1"})
        assert "my-account/orders" in mock_adapter.last_request["url"]
        assert "page=1" in mock_adapter.last_request["url"]

    def test_get_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"id": 42}')
        client.account().get_order(42)
        assert "my-account/orders/42" in mock_adapter.last_request["url"]

    def test_get_guest_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"id": 42}')
        client.account().get_guest_order(42, "guest@example.com")
        assert "my-account/orders/42" in mock_adapter.last_request["url"]
        assert "email=guest%40example.com" in mock_adapter.last_request["url"]


class TestAccountDownloads:
    def test_get_order_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_order_downloads(42)
        assert "my-account/orders/42/downloads" in mock_adapter.last_request["url"]

    def test_get_guest_order_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_guest_order_downloads(42, "guest@example.com")
        assert "my-account/orders/42/downloads" in mock_adapter.last_request["url"]
        assert "email=guest%40example.com" in mock_adapter.last_request["url"]

    def test_get_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_downloads()
        assert "my-account/downloads" in mock_adapter.last_request["url"]


class TestAccountReviews:
    def test_get_reviews(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_reviews()
        assert "my-account/reviews" in mock_adapter.last_request["url"]


class TestAccountNoRoute:
    def test_no_route_raises_plugin_required(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(404, body='{"code":"rest_no_route","message":"No route"}')
        with pytest.raises(CoCartException) as exc_info:
            client.account().get_profile()
        assert exc_info.value.error_code == "cocart_plugin_required"
