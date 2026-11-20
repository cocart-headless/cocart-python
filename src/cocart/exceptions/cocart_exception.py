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

    def get_cart(self) -> Optional[Dict[str, Any]]:
        """The cart sent with the error, when CoCart sends one.

        ``cocart_item_not_in_cart`` (an item key that isn't in the cart)
        carries the cart as it is now, so you can show it without another
        request. ``None`` otherwise.
        """
        cart = self._data().get("cart")
        return cart if isinstance(cart, dict) and cart else None

    def get_fields(self) -> Dict[str, str]:
        """Every field at fault, by path (e.g. ``billing.postcode``), with its message.

        CoCart Plus checks a whole form at once (``data.fields``). Empty when
        the error isn't about fields.
        """
        fields = self._data().get("fields")
        if not isinstance(fields, dict):
            return {}
        return {str(path): message for path, message in fields.items() if isinstance(message, str)}

    def get_field(self) -> Optional[str]:
        """The first field at fault, as a path such as ``billing.postcode``
        (``data.field``), or ``None``."""
        field = self._data().get("field")
        return field if isinstance(field, str) and field != "" else None

    def get_reason(self) -> Optional[str]:
        """The underlying plugin's own reason, when there is one (``data.reason``), or ``None``."""
        reason = self._data().get("reason")
        return reason if isinstance(reason, str) and reason != "" else None

    def _data(self) -> Dict[str, Any]:
        data = self.response_data.get("data")
        return data if isinstance(data, dict) else {}
