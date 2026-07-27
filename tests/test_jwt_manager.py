from __future__ import annotations

import base64
import json
import time

import pytest

from cocart import CoCart
from cocart.exceptions import AuthenticationException, TwoFactorRequiredException
from cocart.jwt_manager import JwtManager
from cocart.storage.memory_storage import MemoryStorage
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


def make_jwt(payload: dict) -> str:
    """Create a mock JWT token with a given payload."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(b"signature").decode().rstrip("=")
    return f"{header}.{body}.{sig}"


class TestJwtManagerLogin:
    def test_login_success(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body=json.dumps({
            "extras": {"jwt_token": "access123", "jwt_refresh": "refresh456"},
        }))
        jwt_mgr = JwtManager(client)
        response = jwt_mgr.login("user", "pass")
        assert response.is_successful()
        assert client.get_jwt_token() == "access123"
        assert client.get_refresh_token() == "refresh456"

    def test_login_missing_jwt(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"extras": {}}')
        jwt_mgr = JwtManager(client)
        with pytest.raises(AuthenticationException, match="JWT token not found"):
            jwt_mgr.login("user", "pass")

    def test_login_requires_2fa(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(401, body=json.dumps({
            "code": "cocart_2fa_required",
            "message": "2FA code required",
            "data": {
                "available_providers": ["email", "totp"],
                "default_provider": "totp",
                "email_sent": True,
            },
        }))
        jwt_mgr = JwtManager(client)
        with pytest.raises(TwoFactorRequiredException) as exc_info:
            jwt_mgr.login("user", "pass")
        assert exc_info.value.available_providers == ["email", "totp"]
        assert exc_info.value.default_provider == "totp"
        assert exc_info.value.email_sent is True


class TestJwtManagerVerifyTwoFactor:
    def test_verify_two_factor_success(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body=json.dumps({
            "extras": {"jwt_token": "access123", "jwt_refresh": "refresh456"},
        }))
        jwt_mgr = JwtManager(client)
        response = jwt_mgr.verify_two_factor("user", "pass", "123456", provider="totp")
        assert response.is_successful()
        assert client.get_jwt_token() == "access123"
        assert client.get_refresh_token() == "refresh456"
        body = json.loads(mock_adapter.last_request["body"])
        assert body["2fa_code"] == "123456"
        assert body["2fa_provider"] == "totp"


class TestJwtManagerRefresh:
    def test_refresh(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.set_refresh_token("old_refresh")
        mock_adapter.queue(200, body=json.dumps({
            "token": "new_access",
            "refresh_token": "new_refresh",
        }))
        jwt_mgr = JwtManager(client)
        jwt_mgr.refresh()
        assert client.get_jwt_token() == "new_access"
        assert client.get_refresh_token() == "new_refresh"

    def test_refresh_no_token(self, client: CoCart) -> None:
        jwt_mgr = JwtManager(client)
        with pytest.raises(AuthenticationException, match="No refresh token"):
            jwt_mgr.refresh()


class TestJwtManagerTokens:
    def test_has_tokens(self, client: CoCart) -> None:
        jwt_mgr = JwtManager(client)
        assert not jwt_mgr.has_tokens()
        client.set_jwt_token("token")
        assert jwt_mgr.has_tokens()

    def test_clear_tokens(self, client: CoCart) -> None:
        client.set_jwt_token("token")
        storage = MemoryStorage()
        storage.set("cocart_jwt_token", "token")
        jwt_mgr = JwtManager(client, storage)
        jwt_mgr.clear_tokens()
        assert not client.has_jwt_token()
        assert storage.get("cocart_jwt_token") is None


class TestJwtManagerExpiry:
    def test_is_token_expired_no_token(self, client: CoCart) -> None:
        jwt_mgr = JwtManager(client)
        assert jwt_mgr.is_token_expired()

    def test_is_token_expired_future(self, client: CoCart) -> None:
        token = make_jwt({"exp": int(time.time()) + 3600})
        client.set_jwt_token(token)
        jwt_mgr = JwtManager(client)
        assert not jwt_mgr.is_token_expired()

    def test_is_token_expired_past(self, client: CoCart) -> None:
        token = make_jwt({"exp": int(time.time()) - 100})
        client.set_jwt_token(token)
        jwt_mgr = JwtManager(client)
        assert jwt_mgr.is_token_expired()

    def test_get_token_expiry(self, client: CoCart) -> None:
        exp = int(time.time()) + 3600
        token = make_jwt({"exp": exp})
        client.set_jwt_token(token)
        jwt_mgr = JwtManager(client)
        assert jwt_mgr.get_token_expiry() == exp

    def test_get_token_expiry_no_token(self, client: CoCart) -> None:
        jwt_mgr = JwtManager(client)
        assert jwt_mgr.get_token_expiry() is None


class TestJwtManagerStorage:
    def test_restore_tokens(self, client: CoCart) -> None:
        storage = MemoryStorage()
        storage.set("cocart_jwt_token", "stored_token")
        storage.set("cocart_jwt_refresh_token", "stored_refresh")
        jwt_mgr = JwtManager(client, storage)
        jwt_mgr.restore_tokens_from_storage()
        assert client.get_jwt_token() == "stored_token"
        assert client.get_refresh_token() == "stored_refresh"

    def test_persist_tokens_on_login(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        storage = MemoryStorage()
        mock_adapter.queue(200, body=json.dumps({
            "extras": {"jwt_token": "access", "jwt_refresh": "refresh"},
        }))
        jwt_mgr = JwtManager(client, storage)
        jwt_mgr.login("user", "pass")
        assert storage.get("cocart_jwt_token") == "access"
        assert storage.get("cocart_jwt_refresh_token") == "refresh"


class TestJwtManagerAutoRefresh:
    def test_auto_refresh_setting(self, client: CoCart) -> None:
        jwt_mgr = JwtManager(client, auto_refresh=True)
        assert jwt_mgr.is_auto_refresh_enabled()
        jwt_mgr.set_auto_refresh(False)
        assert not jwt_mgr.is_auto_refresh_enabled()
