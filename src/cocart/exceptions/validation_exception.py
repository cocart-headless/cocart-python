from __future__ import annotations

from typing import Any, Dict, Optional

from cocart.exceptions.cocart_exception import CoCartException


class ValidationException(CoCartException):
    """Raised on 400 validation errors."""

    def __init__(
        self,
        message: str,
        http_code: int = 400,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, http_code, error_code, response_data)
