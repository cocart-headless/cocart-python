from __future__ import annotations

from typing import Dict, Optional, Protocol

from cocart.http.http_response import HttpResponse


class HttpAdapter(Protocol):
    """Protocol for HTTP adapters."""

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse: ...

    @staticmethod
    def is_available() -> bool: ...

    @staticmethod
    def get_name() -> str: ...
