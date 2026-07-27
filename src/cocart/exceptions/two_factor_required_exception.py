from __future__ import annotations

from typing import Any, Dict, List, Optional

from cocart.exceptions.authentication_exception import AuthenticationException


class TwoFactorRequiredException(AuthenticationException):
    """Raised when the server requires a 2FA code to complete login.

    Thrown when :meth:`JwtManager.login` gets a ``cocart_2fa_required``
    response (the CoCart 2FA plugin is installed and the user has 2FA
    enabled). Catch this, prompt the user for a code, then call
    :meth:`JwtManager.verify_two_factor` to complete the login.
    """

    def __init__(
        self,
        message: str,
        http_code: int = 401,
        error_code: str = "cocart_2fa_required",
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, http_code, error_code, response_data)

        data = response_data or {}
        inner = data.get("data")
        inner = inner if isinstance(inner, dict) else data

        self.available_providers: List[str] = inner.get("available_providers") or []
        self.default_provider: Optional[str] = inner.get("default_provider")
        self.email_sent: bool = bool(inner.get("email_sent", False))
