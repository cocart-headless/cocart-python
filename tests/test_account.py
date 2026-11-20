from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from cocart import CheckoutResult, CoCart
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


@pytest.fixture
def guest(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestAccountProfile:
    def test_get_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"first_name": "John"}')
        response = client.account().get_profile()
        assert response.is_successful()
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account")
        assert mock_adapter.last_request["method"] == "GET"

    def test_get_profile_sends_formatted_and_meta_keys(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().get_profile({"formatted": True, "meta_keys": ["loyalty_tier", "newsletter"]})
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/my-account"
        assert parse_qs(urlsplit(url).query) == {"formatted": ["true"], "meta_keys": ["loyalty_tier,newsletter"]}

    def test_update_profile(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"success": true}')
        client.account().update_profile({"account_first_name": "Jane"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["account_first_name"] == "Jane"
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account")

    def test_change_password_posts_only_the_password_fields_in_one_request(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        client.account().change_password("old_pw", "new_pw", "new_pw")

        assert len(mock_adapter.requests) == 1
        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/my-account"
        assert json.loads(mock_adapter.last_request["body"]) == {
            "password_current": "old_pw",
            "password_1": "new_pw",
            "password_2": "new_pw",
        }

    def test_update_address(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        data = {"billing_address": {"first_name": "Jane", "city": "Paris"}}
        client.account().update_address(data)
        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account/address")
        assert json.loads(mock_adapter.last_request["body"]) == data


class TestAccountOrders:
    def test_get_orders(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"orders": []}')
        client.account().get_orders({"page": "1"})
        assert "my-account/orders" in mock_adapter.last_request["url"]
        assert "page=1" in mock_adapter.last_request["url"]

    def test_get_orders_without_params_sends_no_query(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().get_orders()
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/my-account/orders"

    def test_get_orders_sends_the_filters_joining_lists_with_commas(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        client.account().get_orders({
            "status": ["processing", "on-hold"],
            "after": "2026-01-01T00:00:00",
            "before": "2026-12-31T23:59:59",
            "subscription_order_type": "renewal",
            "formatted": True,
            "meta_keys": ["gift_message", "_configuration"],
        })
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/my-account/orders"
        assert parse_qs(urlsplit(url).query) == {
            "status": ["processing,on-hold"],
            "after": ["2026-01-01T00:00:00"],
            "before": ["2026-12-31T23:59:59"],
            "subscription_order_type": ["renewal"],
            "formatted": ["true"],
            "meta_keys": ["gift_message,_configuration"],
        }

    def test_get_orders_sends_one_status(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().get_orders({"status": "completed", "page": 2, "per_page": 20, "order": "asc"})
        query = parse_qs(urlsplit(mock_adapter.last_request["url"]).query)
        assert query == {"status": ["completed"], "page": ["2"], "per_page": ["20"], "order": ["asc"]}

    def test_get_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"id": 42}')
        client.account().get_order(42)
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/my-account/orders/42"

    def test_get_order_sends_formatted_and_meta_keys(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().get_order(42, {"formatted": False, "meta_keys": ["gift_message"]})
        query = parse_qs(urlsplit(mock_adapter.last_request["url"]).query)
        assert query == {"formatted": ["false"], "meta_keys": ["gift_message"]}

    def test_get_guest_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"id": 42}')
        client.account().get_guest_order(42, "guest@example.com")
        assert "my-account/orders/42" in mock_adapter.last_request["url"]
        assert "email=guest%40example.com" in mock_adapter.last_request["url"]

    def test_get_guest_order_sends_formatted_with_the_email(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        client.account().get_guest_order(42, "guest@example.com", {"formatted": True})
        query = parse_qs(urlsplit(mock_adapter.last_request["url"]).query)
        assert query == {"formatted": ["true"], "email": ["guest@example.com"]}

    def test_cancel_order(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().cancel_order(42)
        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account/orders/42/cancel")
        assert mock_adapter.last_request["body"] is None


class TestAccountDownloads:
    DOWNLOADS = {"downloads": [{"download_id": "abc", "file": {"name": "Guide.pdf"}}]}

    def test_get_order_downloads_calls_the_order_downloads_route(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps(self.DOWNLOADS))
        response = client.account().get_order_downloads(42)
        assert mock_adapter.last_request["method"] == "GET"
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/my-account/orders/42/downloads"
        assert response.to_dict() == self.DOWNLOADS

    def test_get_guest_order_downloads_sends_the_billing_email_to_the_same_route(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps(self.DOWNLOADS))
        response = client.account().get_guest_order_downloads(42, "guest@example.com")
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/my-account/orders/42/downloads"
        assert parse_qs(urlsplit(url).query) == {"email": ["guest@example.com"]}
        assert response.to_dict() == self.DOWNLOADS

    def test_get_downloads(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_downloads()
        assert "my-account/downloads" in mock_adapter.last_request["url"]


class TestAccountReviews:
    def test_get_reviews_uses_products_reviews_mine(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='[]')
        client.account().get_reviews({"per_page": "5"})
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/products/reviews/mine"
        assert "per_page=5" in url


class TestAccountEmailVerification:
    def test_verify_email(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().verify_email("k3y", 7)
        url = mock_adapter.last_request["url"]
        assert mock_adapter.last_request["method"] == "GET"
        assert urlsplit(url).path == "/wp-json/cocart/v2/my-account/verify-email"
        assert parse_qs(urlsplit(url).query) == {"key": ["k3y"], "user_id": ["7"]}

    def test_send_order_email_verification(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().send_order_email_verification()
        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"].endswith("cocart/v2/my-account/verify-order-email")

    def test_verify_order_email(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().verify_order_email("k3y", 7)
        url = mock_adapter.last_request["url"]
        assert mock_adapter.last_request["method"] == "GET"
        assert urlsplit(url).path == "/wp-json/cocart/v2/my-account/verify-order-email"
        assert parse_qs(urlsplit(url).query) == {"key": ["k3y"], "user_id": ["7"]}


class TestAccountSubscriptions:
    def test_subscription_routes(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        account = client.account()
        account.get_subscriptions({"page": 2, "status": ["active", "on-hold"]})
        account.get_subscription(9)
        account.suspend_subscription(9)
        account.reactivate_subscription(9)
        account.cancel_subscription(9)
        account.set_subscription_auto_renew(9, False)
        account.update_subscription_payment_method(9, {"payment_method": "stripe", "token_id": 3})
        account.resubscribe(9)
        account.cancel_resubscribe(9)

        base = "https://example.com/wp-json/cocart/v2/my-account/subscriptions"
        assert [(r["method"], r["url"], r["body"]) for r in mock_adapter.requests] == [
            ("GET", f"{base}?page=2&status=active%2Con-hold", None),
            ("GET", f"{base}/9", None),
            ("POST", f"{base}/9/suspend", None),
            ("POST", f"{base}/9/reactivate", None),
            ("POST", f"{base}/9/cancel", None),
            ("POST", f"{base}/9/auto-renew", '{"enabled": false}'),
            ("POST", f"{base}/9/payment-method", '{"payment_method": "stripe", "token_id": 3}'),
            ("POST", f"{base}/9/resubscribe", None),
            ("DELETE", f"{base}/9/resubscribe", None),
        ]

    def test_get_subscription_as_a_guest(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.account().get_subscription(9, "guest@example.com")
        assert mock_adapter.last_request["url"].endswith("my-account/subscriptions/9?email=guest%40example.com")

    def test_get_subscription_sends_formatted_and_meta_keys(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        client.account().get_subscription(9, params={"formatted": True, "meta_keys": ["a", "b"]})
        query = parse_qs(urlsplit(mock_adapter.last_request["url"]).query)
        assert query == {"formatted": ["true"], "meta_keys": ["a,b"]}

    def test_update_subscription_payment_method_reads_the_subscription_result(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps({
            "object": "subscription",
            "result": {"code": "payment_method_changed", "message": "Payment method updated.", "action": None,
                       "redirect_url": None, "error": None},
            "id": 9,
            "status": {"code": "active", "label": "Active"},
        }))
        result = client.account().update_subscription_payment_method(
            9, {"payment_method": "stripe", "payment_data": {"wc-stripe-payment-method": "pm_card_visa"}}
        )

        assert json.loads(mock_adapter.last_request["body"]) == {
            "payment_method": "stripe",
            "payment_data": [{"key": "wc-stripe-payment-method", "value": "pm_card_visa"}],
        }
        assert isinstance(result, CheckoutResult)
        assert result.is_complete()
        assert result.object == "subscription"
        assert result.subscription_id == 9
        assert result.order_id is None


class TestAccountWithoutLogin:
    def test_request_order_withdrawal(self, guest: CoCart, mock_adapter: MockHttpAdapter) -> None:
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "email_confirmation": "jane@example.com",
            "order_number": "1234",
        }
        guest.account().request_order_withdrawal(data)
        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/order-withdrawal"
        assert json.loads(mock_adapter.last_request["body"]) == data

    def test_register(self, guest: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(201, body=json.dumps({
            "object": "customer",
            "result": {"code": "account_created", "message": "Your account was created."},
            "id": 42,
            "username": "jane",
        }))
        response = guest.account().register("jane@example.com", "jane", "a-strong-password")

        assert mock_adapter.last_request["method"] == "POST"
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/cocart/v2/register"
        # Not username/password: CoCart would treat those as a Basic Auth attempt.
        assert json.loads(mock_adapter.last_request["body"]) == {
            "email": "jane@example.com",
            "requested_username": "jane",
            "requested_password": "a-strong-password",
        }
        assert "Authorization" not in mock_adapter.last_request["headers"]
        assert response.status_code == 201
        assert response.get("id") == 42

    def test_register_with_only_an_email(self, guest: CoCart, mock_adapter: MockHttpAdapter) -> None:
        guest.account().register("jane@example.com")
        assert json.loads(mock_adapter.last_request["body"]) == {"email": "jane@example.com"}


class TestAccountNoRoute:
    def test_no_route_raises_plugin_required(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(404, body='{"code":"rest_no_route","message":"No route"}')
        with pytest.raises(CoCartException) as exc_info:
            client.account().get_profile()
        assert exc_info.value.error_code == "cocart_plugin_required"
