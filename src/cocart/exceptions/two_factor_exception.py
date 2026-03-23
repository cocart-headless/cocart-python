from __future__ import annotations

from cocart.exceptions.authentication_exception import AuthenticationException


class TwoFactorRequiredException(AuthenticationException):
    """Raised when the server requires a 2FA code to complete login.

    Thrown by the client when the login endpoint returns a 401 with
    ``code: cocart_2fa_required``. Catch this exception, inspect
    :attr:`available_providers` and :attr:`default_provider`, prompt
    the user for a code, then call :meth:`~cocart.JwtManager.login_with_2fa`
    to complete authentication.
    """

    @property
    def available_providers(self) -> list[str]:
        """Providers available for verification (e.g. ``'totp'``, ``'email'``, ``'backup'``)."""
        return (self.response_data or {}).get("data", {}).get("available_providers", [])

    @property
    def default_provider(self) -> str | None:
        """The default provider the server will use if none is specified."""
        return (self.response_data or {}).get("data", {}).get("default_provider")

    @property
    def email_sent(self) -> bool:
        """Whether the server has already sent a verification code via email."""
        return bool((self.response_data or {}).get("data", {}).get("email_sent", False))
