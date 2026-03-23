from __future__ import annotations

import json

import pytest

from cocart import CoCart
from cocart.exceptions import AuthenticationException
from cocart.exceptions.two_factor_exception import TwoFactorRequiredException
from cocart.jwt_manager import JwtManager
from cocart.storage.memory_storage import MemoryStorage
from tests.mock_http_adapter import MockHttpAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TWO_FA_RESPONSE = {
    "code": "cocart_2fa_required",
    "message": "Two factor authentication is required.",
    "data": {
        "status": 401,
        "2fa_required": True,
        "available_providers": ["totp", "email"],
        "default_provider": "totp",
        "email_sent": False,
    },
}

TWO_FA_EMAIL_RESPONSE = {
    "code": "cocart_2fa_required",
    "message": "Two factor authentication is required.",
    "data": {
        "status": 401,
        "2fa_required": True,
        "available_providers": ["email"],
        "default_provider": "email",
        "email_sent": True,
    },
}

LOGIN_SUCCESS_RESPONSE = {
    "extras": {"jwt_token": "access123", "jwt_refresh": "refresh456"},
}


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


# ---------------------------------------------------------------------------
# TwoFactorRequiredException — class properties
# ---------------------------------------------------------------------------

class TestTwoFactorRequiredException:
    def test_available_providers(self) -> None:
        exc = TwoFactorRequiredException(
            "2FA required",
            401,
            "cocart_2fa_required",
            TWO_FA_RESPONSE,
        )
        assert exc.available_providers == ["totp", "email"]

    def test_default_provider(self) -> None:
        exc = TwoFactorRequiredException(
            "2FA required",
            401,
            "cocart_2fa_required",
            TWO_FA_RESPONSE,
        )
        assert exc.default_provider == "totp"

    def test_email_sent_false(self) -> None:
        exc = TwoFactorRequiredException(
            "2FA required",
            401,
            "cocart_2fa_required",
            TWO_FA_RESPONSE,
        )
        assert exc.email_sent is False

    def test_email_sent_true(self) -> None:
        exc = TwoFactorRequiredException(
            "2FA required",
            401,
            "cocart_2fa_required",
            TWO_FA_EMAIL_RESPONSE,
        )
        assert exc.email_sent is True

    def test_empty_data_defaults(self) -> None:
        exc = TwoFactorRequiredException("2FA required", 401, "cocart_2fa_required", {})
        assert exc.available_providers == []
        assert exc.default_provider is None
        assert exc.email_sent is False

    def test_is_subclass_of_authentication_exception(self) -> None:
        exc = TwoFactorRequiredException("2FA required", 401, "cocart_2fa_required", {})
        assert isinstance(exc, AuthenticationException)


# ---------------------------------------------------------------------------
# JwtManager.login() — 2FA detection
# ---------------------------------------------------------------------------

class TestJwtManagerLoginTwoFactor:
    def test_login_raises_two_factor_exception_on_challenge(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(401, body=json.dumps(TWO_FA_RESPONSE))
        jwt_mgr = JwtManager(client)
        with pytest.raises(TwoFactorRequiredException) as exc_info:
            jwt_mgr.login("user", "pass")
        assert exc_info.value.available_providers == ["totp", "email"]
        assert exc_info.value.default_provider == "totp"

    def test_login_two_factor_exception_has_email_sent_flag(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(401, body=json.dumps(TWO_FA_EMAIL_RESPONSE))
        jwt_mgr = JwtManager(client)
        with pytest.raises(TwoFactorRequiredException) as exc_info:
            jwt_mgr.login("user", "pass")
        assert exc_info.value.email_sent is True

    def test_login_regular_401_raises_authentication_exception(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(401, body=json.dumps({
            "code": "cocart_authentication_error",
            "message": "Invalid credentials.",
        }))
        jwt_mgr = JwtManager(client)
        with pytest.raises(AuthenticationException) as exc_info:
            jwt_mgr.login("user", "wrong_pass")
        assert not isinstance(exc_info.value, TwoFactorRequiredException)


# ---------------------------------------------------------------------------
# JwtManager.login_with_2fa()
# ---------------------------------------------------------------------------

class TestJwtManagerLoginWith2FA:
    def test_sends_correct_payload_without_provider(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps(LOGIN_SUCCESS_RESPONSE))
        jwt_mgr = JwtManager(client)
        jwt_mgr.login_with_2fa("user", "pass", "123456")

        body = json.loads(mock_adapter.last_request["body"] or "{}")
        assert body["username"] == "user"
        assert body["password"] == "pass"
        assert body["2fa_code"] == "123456"
        assert "2fa_provider" not in body

    def test_sends_correct_payload_with_provider(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps(LOGIN_SUCCESS_RESPONSE))
        jwt_mgr = JwtManager(client)
        jwt_mgr.login_with_2fa("user", "pass", "123456", provider="email")

        body = json.loads(mock_adapter.last_request["body"] or "{}")
        assert body["2fa_code"] == "123456"
        assert body["2fa_provider"] == "email"

    def test_extracts_tokens_on_success(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body=json.dumps(LOGIN_SUCCESS_RESPONSE))
        jwt_mgr = JwtManager(client)
        jwt_mgr.login_with_2fa("user", "pass", "123456")
        assert client.get_jwt_token() == "access123"
        assert client.get_refresh_token() == "refresh456"

    def test_raises_when_no_jwt_in_response(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body='{"extras": {}}')
        jwt_mgr = JwtManager(client)
        with pytest.raises(AuthenticationException, match="JWT token not found"):
            jwt_mgr.login_with_2fa("user", "pass", "123456")

    def test_persists_tokens_to_storage(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        storage = MemoryStorage()
        mock_adapter.queue(200, body=json.dumps(LOGIN_SUCCESS_RESPONSE))
        jwt_mgr = JwtManager(client, storage)
        jwt_mgr.login_with_2fa("user", "pass", "123456")
        assert storage.get("cocart_jwt_token") == "access123"
        assert storage.get("cocart_jwt_refresh_token") == "refresh456"


# ---------------------------------------------------------------------------
# JwtManager.with_auto_refresh() — must NOT retry on 2FA challenge
# ---------------------------------------------------------------------------

class TestJwtManagerAutoRefreshTwoFactor:
    def test_auto_refresh_does_not_trigger_on_2fa_challenge(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        client.set_refresh_token("some_refresh_token")
        # Queue a 2FA challenge to be returned by the callback
        mock_adapter.queue(401, body=json.dumps(TWO_FA_RESPONSE))

        jwt_mgr = JwtManager(client)
        call_count = 0

        def callback(_client: CoCart) -> None:
            nonlocal call_count
            call_count += 1
            _client.post("login", {"username": "user", "password": "pass"})

        with pytest.raises(TwoFactorRequiredException):
            jwt_mgr.with_auto_refresh(callback)

        # Callback must only have been called once — no retry after 2FA challenge
        assert call_count == 1
