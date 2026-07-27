from __future__ import annotations

import json

import pytest

from cocart import CoCart
from cocart.exceptions import AuthenticationException, CoCartException, ValidationException, VersionException
from tests.mock_http_adapter import MockHttpAdapter


class TestConstructor:
    def test_default_options(self) -> None:
        c = CoCart("https://example.com")
        assert c.get_store_url() == "https://example.com"
        assert c.get_rest_prefix() == "wp-json"
        assert c.get_namespace() == "cocart"
        assert c.get_main_plugin() == "basic"
        assert c.is_guest()
        assert not c.is_authenticated()
        assert c.get_cart_key() is None

    def test_strips_trailing_slash(self) -> None:
        c = CoCart("https://example.com///")
        assert c.get_store_url() == "https://example.com"

    def test_with_basic_auth(self) -> None:
        c = CoCart("https://example.com", username="user", password="pass")
        assert c.is_authenticated()
        assert not c.is_guest()

    def test_with_jwt_token(self) -> None:
        c = CoCart("https://example.com", jwt_token="token123")
        assert c.is_authenticated()
        assert c.get_jwt_token() == "token123"

    def test_with_cart_key(self) -> None:
        c = CoCart("https://example.com", cart_key="abc123")
        assert c.get_cart_key() == "abc123"

    def test_with_custom_options(self) -> None:
        c = CoCart(
            "https://example.com",
            rest_prefix="api",
            namespace="mystore",
            timeout=60,
            max_retries=3,
            main_plugin="legacy",
        )
        assert c.get_rest_prefix() == "api"
        assert c.get_namespace() == "mystore"
        assert c.get_main_plugin() == "legacy"


class TestFluentInterface:
    def test_set_cart_key_returns_self(self) -> None:
        c = CoCart("https://example.com")
        result = c.set_cart_key("abc")
        assert result is c
        assert c.get_cart_key() == "abc"

    def test_chaining(self) -> None:
        c = CoCart("https://example.com")
        result = c.set_timeout(60).set_max_retries(3).set_debug(True)
        assert result is c


class TestAuthentication:
    def test_set_auth(self) -> None:
        c = CoCart("https://example.com")
        c.set_auth("user", "pass")
        assert c.is_authenticated()
        assert not c.is_guest()

    def test_set_jwt_clears_basic_auth(self) -> None:
        c = CoCart("https://example.com", username="user", password="pass")
        c.set_jwt_token("token")
        assert c.get_jwt_token() == "token"
        assert c.has_jwt_token()

    def test_set_auth_clears_jwt(self) -> None:
        c = CoCart("https://example.com", jwt_token="token")
        c.set_auth("user", "pass")
        assert c.get_jwt_token() is None

    def test_clear_jwt_token(self) -> None:
        c = CoCart("https://example.com", jwt_token="token", jwt_refresh_token="refresh")
        c.clear_jwt_token()
        assert c.get_jwt_token() is None
        assert c.get_refresh_token() is None
        assert not c.has_jwt_token()

    def test_woocommerce_credentials(self) -> None:
        c = CoCart("https://example.com")
        c.set_woocommerce_credentials("ck_123", "cs_456")
        # WooCommerce creds don't set is_authenticated (no _auth or _jwt_token)
        assert c.is_guest()

    def test_clear_session(self) -> None:
        c = CoCart("https://example.com", username="user", password="pass", cart_key="key")
        c.clear_session()
        assert c.is_guest()
        assert c.get_cart_key() is None


class TestUrlBuilding:
    def test_default_url(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"ok": true}')
        client.get("cart")
        assert mock_adapter.last_request is not None
        assert "https://example.com/wp-json/cocart/v2/cart" in mock_adapter.last_request["url"]

    def test_custom_prefix_and_namespace(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", rest_prefix="api", namespace="mystore")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body='{"ok": true}')
        c.get("products")
        assert "https://example.com/api/mystore/v2/products" in mock_adapter.last_request["url"]

    def test_cart_key_added_for_guest(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", cart_key="guestkey")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        assert "cart_key=guestkey" in mock_adapter.last_request["url"]

    def test_cart_key_not_added_for_authenticated(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", username="u", password="p", cart_key="guestkey")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        assert "cart_key=" not in mock_adapter.last_request["url"]

    def test_fields_normalization_basic(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="{}")
        client.get("cart", {"fields": "items,totals"})
        assert "_fields=items%2Ctotals" in mock_adapter.last_request["url"]

    def test_fields_normalization_legacy(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart", {"_fields": "items"})
        assert "fields=items" in mock_adapter.last_request["url"]


class TestHeaders:
    def test_default_headers(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="{}")
        client.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "CoCart-Python-SDK" in headers["User-Agent"]

    def test_basic_auth_header(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", username="admin", password="secret")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["Authorization"].startswith("Basic ")

    def test_jwt_auth_header(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", jwt_token="mytoken")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["Authorization"] == "Bearer mytoken"

    def test_custom_auth_header_name(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", jwt_token="mytoken", auth_header_name="X-Auth")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["X-Auth"] == "Bearer mytoken"

    def test_cart_key_header_for_guest(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", cart_key="guest123")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["Cart-Key"] == "guest123"
        assert "CoCart-API-Cart-Key" not in headers

    def test_cart_key_header_for_legacy_plugin(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", cart_key="guest123", main_plugin="legacy")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["CoCart-API-Cart-Key"] == "guest123"
        assert "Cart-Key" not in headers

    def test_custom_headers(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", headers={"X-Custom": "value"})
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        headers = mock_adapter.last_request["headers"]
        assert headers["X-Custom"] == "value"


class TestErrorHandling:
    def test_authentication_error(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(401, body='{"code":"rest_forbidden","message":"Unauthorized"}')
        with pytest.raises(AuthenticationException) as exc_info:
            client.get("cart")
        assert exc_info.value.http_code == 401

    def test_validation_error(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(400, body='{"code":"cocart_invalid_product","message":"Invalid product"}')
        with pytest.raises(ValidationException) as exc_info:
            client.post("cart/add-item", {"id": "0"})
        assert exc_info.value.http_code == 400

    def test_generic_error(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(500, body='{"code":"server_error","message":"Server error"}')
        with pytest.raises(CoCartException) as exc_info:
            client.get("cart")
        assert exc_info.value.http_code == 500


class TestETag:
    def test_etag_caching(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, headers={"etag": '"abc123"'}, body='{"items":[]}')
        client.get("cart")

        mock_adapter.queue(304, body="")
        client.get("cart")

        second_headers = mock_adapter.requests[1]["headers"]
        assert second_headers.get("If-None-Match") == '"abc123"'

    def test_etag_disabled(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", etag=False)
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        mock_adapter.queue(200, headers={"etag": '"abc"'}, body="{}")
        c.get("cart")
        mock_adapter.queue(200, body="{}")
        c.get("cart")
        assert "If-None-Match" not in mock_adapter.requests[1]["headers"]

    def test_etag_304_returns_cached_body(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, headers={"etag": '"abc123"'}, body='{"items":["widget"]}')
        first = client.get("cart")
        assert first.to_dict() == {"items": ["widget"]}

        mock_adapter.queue(304, body="")
        second = client.get("cart")
        assert second.status_code == 304
        assert second.to_dict() == {"items": ["widget"]}


class TestCartKeyExtraction:
    def test_extracts_cart_key_from_response_header(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, headers={"cart-key": "newkey123"}, body="{}")
        client.get("cart")
        assert client.get_cart_key() == "newkey123"


class TestEvents:
    def test_on_and_off(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        events = []

        def listener(data: dict) -> None:
            events.append(data)

        client.on("request", listener)
        mock_adapter.queue(200, body="{}")
        client.get("cart")
        assert len(events) == 1
        assert events[0]["method"] == "GET"

        client.off("request", listener)
        mock_adapter.queue(200, body="{}")
        client.get("cart")
        assert len(events) == 1

    def test_response_event(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        events = []
        client.on("response", lambda d: events.append(d))
        mock_adapter.queue(200, body="{}")
        client.get("cart")
        assert len(events) == 1
        assert events[0]["status"] == 200


class TestRequiresBasic:
    def test_raises_version_exception_for_legacy(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.requires_basic("products().find_by_slug")

    def test_passes_for_basic(self) -> None:
        c = CoCart("https://example.com", main_plugin="basic")
        c.requires_basic("products().find_by_slug")  # Should not raise


class TestRequestRaw:
    def test_request_raw_bypasses_namespace(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"token":"abc"}')
        client.request_raw("POST", "cocart/jwt/refresh-token", data={"refresh_token": "rt"})
        assert "cocart/jwt/refresh-token" in mock_adapter.last_request["url"]
        assert "/v2/" not in mock_adapter.last_request["url"]


class TestRetryJitter:
    def test_retry_delay_has_jitter(self, client: CoCart) -> None:
        # ±20% jitter around a base of 1s (attempt=2 => base 2^(2-1)=2s... use attempt=1 => base=1s)
        delays = {client._get_retry_delay(1) for _ in range(50)}
        assert len(delays) > 1  # jitter produces varying delays
        for delay in delays:
            assert 0.8 <= delay <= 1.2

    def test_retry_after_header_ignores_jitter(self, client: CoCart) -> None:
        from cocart.response import Response

        response = Response(429, {"Retry-After": "5"}, "{}")
        assert client._get_retry_delay(1, response) == 5.0


class TestInFlightGetDedup:
    def test_concurrent_identical_gets_share_one_request(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        import threading
        import time as time_module

        real_request = mock_adapter.request
        call_count = {"n": 0}
        lock = threading.Lock()

        def slow_request(*args: object, **kwargs: object):
            with lock:
                call_count["n"] += 1
            time_module.sleep(0.05)
            return real_request(*args, **kwargs)  # type: ignore[arg-type]

        mock_adapter.queue(200, body='{"ok": true}')
        mock_adapter.request = slow_request  # type: ignore[assignment]

        results = []
        errors = []

        def do_get() -> None:
            try:
                results.append(client.get("cart"))
            except Exception as e:  # pragma: no cover - defensive
                errors.append(e)

        threads = [threading.Thread(target=do_get) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert call_count["n"] == 1
        assert len(results) == 5


class TestBatch:
    def test_batch_posts_requests(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"cart_hash": "abc"}')
        client.batch([
            {"method": "POST", "path": "/cocart/v2/cart/item/k1", "body": {"quantity": "2"}},
        ])
        assert "cocart/batch" in mock_adapter.last_request["url"]
        body = json.loads(mock_adapter.last_request["body"])
        assert body["requests"][0]["path"] == "/cocart/v2/cart/item/k1"

    def test_batch_requires_at_least_one_request(self, client: CoCart) -> None:
        with pytest.raises(ValidationException, match="at least one request"):
            client.batch([])

    def test_batch_no_route_raises_plugin_required(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(404, body='{"code":"rest_no_route","message":"No route"}')
        with pytest.raises(CoCartException) as exc_info:
            client.batch([{"method": "POST", "path": "/cocart/v2/cart/clear"}])
        assert exc_info.value.error_code == "cocart_plugin_required"
