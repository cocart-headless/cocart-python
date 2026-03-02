from __future__ import annotations

from cocart.exceptions.cocart_exception import CoCartException


class VersionException(CoCartException):
    """Raised when a method requires CoCart Basic but the legacy plugin is configured."""

    def __init__(self, method: str) -> None:
        super().__init__(
            f"{method}() requires CoCart Basic. "
            "Please upgrade from the legacy CoCart plugin to use this feature.",
            http_code=0,
            error_code="cocart_version_required",
        )
