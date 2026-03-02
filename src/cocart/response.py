from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, cast


class Response:
    """Response wrapper for CoCart API responses.

    Provides dot-notation access, cart helpers, pagination helpers,
    and error helpers.
    """

    def __init__(self, status_code: int, headers: Dict[str, str], body: str) -> None:
        self.status_code = status_code
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.body = body
        self._data: Any = None

    # --- Data access ---

    def to_dict(self) -> Any:
        """Get decoded response data as a dictionary."""
        if self._data is None:
            try:
                self._data = json.loads(self.body)
            except (json.JSONDecodeError, TypeError):
                self._data = {}
        return self._data

    def to_json(self, pretty: bool = True) -> str:
        """Get response as a JSON string."""
        return json.dumps(self.to_dict(), indent=2 if pretty else None)

    def is_successful(self) -> bool:
        """Check if the response was successful (2xx)."""
        return 200 <= self.status_code < 300

    def is_error(self) -> bool:
        """Check if the response was an error (4xx/5xx)."""
        return self.status_code >= 400

    # --- Dot-notation access ---

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the response data using dot notation.

        Example::

            response.get("totals.subtotal")
            response.get("items.0.name")
        """
        data = self.to_dict()
        for k in key.split("."):
            if isinstance(data, dict):
                data = data.get(k)
            elif isinstance(data, list) and k.isdigit():
                idx = int(k)
                data = data[idx] if idx < len(data) else None
            else:
                return default
            if data is None:
                return default
        return data

    def has(self, key: str) -> bool:
        """Check if the response data contains a key (dot notation)."""
        data = self.to_dict()
        for k in key.split("."):
            if isinstance(data, dict):
                if k not in data:
                    return False
                data = data[k]
            elif isinstance(data, list) and k.isdigit():
                idx = int(k)
                if idx >= len(data):
                    return False
                data = data[idx]
            else:
                return False
        return True

    # --- Header access ---

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a response header (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    # --- Cart helpers ---

    def get_cart_key(self) -> Optional[str]:
        """Get cart key from the Cart-Key response header."""
        return self.get_header("Cart-Key")

    def get_cart_hash(self) -> Optional[str]:
        """Get cart hash from response data."""
        return cast(Optional[str], self.get("cart_hash"))

    def get_items(self) -> List[Dict[str, Any]]:
        """Get cart items from response data."""
        return cast(List[Dict[str, Any]], self.get("items", []))

    def get_totals(self) -> Dict[str, Any]:
        """Get cart totals from response data."""
        return cast(Dict[str, Any], self.get("totals", {}))

    def get_item_count(self) -> int:
        """Get item count from response data."""
        return cast(int, self.get("item_count", 0))

    def has_items(self) -> bool:
        """Check if cart has items."""
        return self.get_item_count() > 0

    def is_empty(self) -> bool:
        """Check if cart is empty."""
        return self.get_item_count() == 0

    def get_notices(self) -> List[Any]:
        """Get notices from response data."""
        return cast(List[Any], self.get("notices", []))

    def get_coupons(self) -> List[Dict[str, Any]]:
        """Get applied coupons from response data."""
        return cast(List[Dict[str, Any]], self.get("coupons", []))

    def has_coupons(self) -> bool:
        """Check if cart has coupons applied."""
        return len(self.get_coupons()) > 0

    def get_customer(self) -> Dict[str, Any]:
        """Get customer details from response data."""
        return cast(Dict[str, Any], self.get("customer", {}))

    def get_currency(self) -> Dict[str, Any]:
        """Get currency information from response data."""
        return cast(Dict[str, Any], self.get("currency", {}))

    def get_shipping_methods(self) -> List[Dict[str, Any]]:
        """Get shipping methods from response data."""
        return cast(List[Dict[str, Any]], self.get("shipping", []))

    def get_fees(self) -> List[Dict[str, Any]]:
        """Get cart fees from response data."""
        return cast(List[Dict[str, Any]], self.get("fees", []))

    def get_cross_sells(self) -> List[Dict[str, Any]]:
        """Get cross-sell products from response data."""
        return cast(List[Dict[str, Any]], self.get("cross_sells", []))

    # --- Pagination helpers ---

    def get_total_results(self) -> Optional[int]:
        """Get total number of results (from X-WP-Total header)."""
        total = self.get_header("X-WP-Total")
        if total is not None:
            try:
                return int(total)
            except ValueError:
                pass
        return None

    def get_total_pages(self) -> Optional[int]:
        """Get total number of pages (from X-WP-TotalPages header)."""
        pages = self.get_header("X-WP-TotalPages")
        if pages is not None:
            try:
                return int(pages)
            except ValueError:
                pass
        return None

    # --- Cache helpers ---

    def get_etag(self) -> Optional[str]:
        """Get the ETag header value."""
        return self.get_header("ETag")

    def is_not_modified(self) -> bool:
        """Check if the response is a 304 Not Modified."""
        return self.status_code == 304

    def get_cache_status(self) -> Optional[str]:
        """Get the CoCart-Cache header value (HIT, MISS, or SKIP)."""
        return self.get_header("CoCart-Cache")

    # --- Error helpers ---

    def get_error_code(self) -> Optional[str]:
        """Get the API error code from an error response."""
        if not self.is_error():
            return None
        return cast(Optional[str], self.get("code"))

    def get_error_message(self) -> Optional[str]:
        """Get the error message from an error response."""
        if not self.is_error():
            return None
        return cast(Optional[str], self.get("message"))
