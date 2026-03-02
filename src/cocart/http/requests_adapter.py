from __future__ import annotations

from typing import Dict, Optional

from cocart.http.http_response import HttpResponse


class RequestsAdapter:
    """HTTP adapter using the ``requests`` library."""

    def __init__(self) -> None:
        import requests

        self._session = requests.Session()

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        import requests

        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=body.encode("utf-8") if body else None,
                timeout=timeout,
                verify=verify_ssl,
            )
        except requests.exceptions.Timeout:
            from cocart.exceptions.cocart_exception import CoCartException

            raise CoCartException(
                f"Request timed out after {timeout}s",
                http_code=0,
                error_code="request_timeout",
            )
        except requests.exceptions.ConnectionError as e:
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
            import requests  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def get_name() -> str:
        return "requests"
