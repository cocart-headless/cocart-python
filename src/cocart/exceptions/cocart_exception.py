from __future__ import annotations

from typing import Any, Dict, Optional


class CoCartException(Exception):
    """Base exception for all CoCart SDK errors."""

    def __init__(
        self,
        message: str,
        http_code: int = 0,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.http_code = http_code
        self.error_code = error_code
        self.response_data = response_data or {}
