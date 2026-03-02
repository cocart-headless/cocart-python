from __future__ import annotations

from typing import Dict, Optional

from cocart.http.http_response import HttpResponse


class HttpxAdapter:
    """HTTP adapter using the ``httpx`` library (optional dependency)."""

    def __init__(self) -> None:
        import httpx

        self._client = httpx.Client()

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        import httpx

        try:
            resp = self._client.request(
                method=method,
                url=url,
                headers=headers,
                content=body.encode("utf-8") if body else None,
                timeout=timeout,
            )
        except httpx.TimeoutException:
            from cocart.exceptions.cocart_exception import CoCartException

            raise CoCartException(
                f"Request timed out after {timeout}s",
                http_code=0,
                error_code="request_timeout",
            )
        except httpx.ConnectError as e:
            from cocart.exceptions.cocart_exception import CoCartException

            raise CoCartException(
                f"Connection error: {e}",
                http_code=0,
                error_code="network_error",
            )

        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        return HttpResponse(
            status_code=resp.status_code,
            headers=resp_headers,
            body=resp.text,
        )

    @staticmethod
    def is_available() -> bool:
        try:
            import httpx  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def get_name() -> str:
        return "httpx"
