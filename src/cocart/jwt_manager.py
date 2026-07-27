from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from cocart.exceptions.authentication_exception import AuthenticationException
from cocart.exceptions.two_factor_required_exception import TwoFactorRequiredException

if TYPE_CHECKING:
    from cocart.cocart import CoCart
    from cocart.response import Response


class JwtManager:
    """JWT Manager — handles JWT token lifecycle.

    Manages token acquisition via login, refresh, validation,
    and optional persistence using a storage adapter.
    """

    def __init__(
        self,
        client: CoCart,
        storage: Any = None,
        auto_refresh: bool = False,
        token_storage_key: str = "cocart_jwt_token",
        refresh_token_storage_key: str = "cocart_jwt_refresh_token",
    ) -> None:
        self._client = client
        self._storage = storage
        self._auto_refresh = auto_refresh
        self._token_storage_key = token_storage_key
        self._refresh_token_storage_key = refresh_token_storage_key
        self._is_refreshing = False

    def restore_tokens_from_storage(self) -> None:
        """Restore tokens from storage into the client."""
        if not self._storage:
            return

        stored_token = self._storage.get(self._token_storage_key)
        stored_refresh = self._storage.get(self._refresh_token_storage_key)

        if stored_token:
            self._client.set_jwt_token(stored_token)
        if stored_refresh:
            self._client.set_refresh_token(stored_refresh)

    def login(self, username: str, password: str) -> Response:
        """Login with username and password to acquire JWT tokens.

        Requires the CoCart JWT Authentication plugin. Raises
        :class:`AuthenticationException` if the plugin isn't installed.

        If the CoCart 2FA plugin is installed and the user has 2FA enabled,
        raises :class:`TwoFactorRequiredException` (carrying the available
        providers). Catch it, prompt for a code, then call
        :meth:`verify_two_factor` to complete login.
        """
        response = self._client.post("login", {"username": username, "password": password})
        return self._extract_and_persist_tokens(response)

    def verify_two_factor(
        self,
        username: str,
        password: str,
        code: str,
        provider: Optional[str] = None,
    ) -> Response:
        """Complete login after a 2FA challenge.

        Call this after catching :class:`TwoFactorRequiredException` from
        :meth:`login`.

        Args:
            username: Username, email, or phone.
            password: Password.
            code: The 2FA verification code from the user.
            provider: Provider name (e.g. ``"email"``, ``"totp"``); omit to use
                the server's default.
        """
        body: Dict[str, str] = {"username": username, "password": password, "2fa_code": code}
        if provider:
            body["2fa_provider"] = provider

        response = self._client.post("login", body)
        return self._extract_and_persist_tokens(response)

    def refresh(self, refresh_token: Optional[str] = None) -> Response:
        """Refresh the JWT access token using the refresh token."""
        token = refresh_token or self._client.get_refresh_token()

        if not token:
            raise AuthenticationException(
                "No refresh token available. Please login first.",
                http_code=0,
                error_code="cocart_jwt_no_refresh_token",
            )

        route = f"{self._client.get_namespace()}/jwt/refresh-token"
        response = self._client.request_raw("POST", route, data={"refresh_token": token})

        data = response.to_dict()
        new_token = data.get("token") if isinstance(data, dict) else None
        new_refresh = data.get("refresh_token") if isinstance(data, dict) else None

        if new_token:
            self._client.set_jwt_token(new_token)
        if new_refresh:
            self._client.set_refresh_token(new_refresh)

        self._persist_tokens()
        return response

    def validate(self) -> bool:
        """Validate the current JWT token with the server."""
        if not self._client.has_jwt_token():
            return False

        try:
            route = f"{self._client.get_namespace()}/jwt/validate-token"
            response = self._client.request_raw("POST", route)
            return response.is_successful()
        except AuthenticationException:
            return False

    def with_auto_refresh(self, callback: Any) -> Any:
        """Execute a callback with automatic token refresh on authentication error."""
        try:
            return callback(self._client)
        except AuthenticationException as e:
            if (
                not isinstance(e, TwoFactorRequiredException)
                and not self._is_refreshing
                and self._client.get_refresh_token()
            ):
                self._is_refreshing = True
                try:
                    self.refresh()
                    result = callback(self._client)
                    return result
                except Exception:
                    raise e
                finally:
                    self._is_refreshing = False
            raise

    def clear_tokens(self) -> JwtManager:
        """Clear all JWT tokens from client and storage."""
        self._client.clear_jwt_token()
        if self._storage:
            self._storage.delete(self._token_storage_key)
            self._storage.delete(self._refresh_token_storage_key)
        return self

    def has_tokens(self) -> bool:
        """Check if tokens are available."""
        return self._client.has_jwt_token()

    def is_token_expired(self, leeway: int = 30) -> bool:
        """Check if the current JWT token is expired by decoding its payload.

        Args:
            leeway: Seconds of leeway before actual expiry.
        """
        token = self._client.get_jwt_token()
        if not token:
            return True

        payload = self._decode_token_payload(token)
        if not payload:
            return True
        if "exp" not in payload:
            return False

        return bool(time.time() >= payload["exp"] - leeway)

    def get_token_expiry(self) -> Optional[int]:
        """Get the expiry timestamp of the current JWT token."""
        token = self._client.get_jwt_token()
        if not token:
            return None

        payload = self._decode_token_payload(token)
        if payload:
            return payload.get("exp")
        return None

    def set_auto_refresh(self, enabled: bool) -> JwtManager:
        self._auto_refresh = enabled
        return self

    def is_auto_refresh_enabled(self) -> bool:
        return self._auto_refresh

    def get_client(self) -> CoCart:
        return self._client

    # --- Internal ---

    def _extract_and_persist_tokens(self, response: Response) -> Response:
        """Extract ``jwt_token``/``jwt_refresh`` from a login response's
        ``extras`` field, set them on the client, and persist them to storage.

        Shared by :meth:`login` and :meth:`verify_two_factor`.
        """
        data = response.to_dict()
        extras = data.get("extras", {}) if isinstance(data, dict) else {}
        jwt_token = extras.get("jwt_token") if isinstance(extras, dict) else None
        refresh_token = extras.get("jwt_refresh") if isinstance(extras, dict) else None

        if jwt_token:
            self._client.set_jwt_token(jwt_token)
            if refresh_token:
                self._client.set_refresh_token(refresh_token)
            self._persist_tokens()
        else:
            raise AuthenticationException(
                "JWT token not found in login response. Is the CoCart JWT Authentication plugin installed?",
                http_code=0,
                error_code="cocart_jwt_missing",
            )

        return response

    def _decode_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode the payload section of a JWT token without verification."""
        parts = token.split(".")
        if len(parts) != 3:
            return None

        try:
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            return cast(Dict[str, Any], json.loads(payload_bytes))
        except Exception:
            return None

    def _persist_tokens(self) -> None:
        if not self._storage:
            return

        token = self._client.get_jwt_token()
        refresh_token = self._client.get_refresh_token()

        if token:
            self._storage.set(self._token_storage_key, token)
        if refresh_token:
            self._storage.set(self._refresh_token_storage_key, refresh_token)
