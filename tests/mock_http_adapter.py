from __future__ import annotations

from typing import Dict, List, Optional

from cocart.http.http_response import HttpResponse


class MockHttpAdapter:
    """Mock HTTP adapter for testing — returns queued responses."""

    def __init__(self) -> None:
        self.responses: List[HttpResponse] = []
        self.requests: List[Dict[str, Optional[str]]] = []

    def queue(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        body: str = "{}",
    ) -> MockHttpAdapter:
        """Queue a response to be returned by the next request."""
        self.responses.append(HttpResponse(status_code, headers or {}, body))
        return self

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        self.requests.append({
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
        })
        if self.responses:
            return self.responses.pop(0)
        return HttpResponse(200, {}, "{}")

    @property
    def last_request(self) -> Optional[Dict[str, Optional[str]]]:
        return self.requests[-1] if self.requests else None

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def get_name() -> str:
        return "mock"
