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

    def get_notices(self) -> Dict[str, List[str]]:
        """Get notices from response data, keyed by type.

        CoCart sends notices keyed by type (``success``, ``error``,
        ``notice``, ``info``), each a list of messages, e.g.
        ``{"success": ["“Beanie” has been added to your cart."]}``.
        ``{}`` when there are none (CoCart 4.x sent ``[]``).
        """
        notices = self.get("notices", {})
        return cast(Dict[str, List[str]], notices) if isinstance(notices, dict) else {}

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
        """Get the shipping packages from response data, as a list.

        Each package has its ``rates`` keyed by rate ID, and ``chosen_method``.
        CoCart sends the packages keyed by package ID under ``shipping.packages``;
        see :meth:`get_shipping` for the whole ``shipping`` field.
        """
        shipping = self.get("shipping")
        if isinstance(shipping, list):
            return cast(List[Dict[str, Any]], shipping)
        if not isinstance(shipping, dict):
            return []
        packages = shipping.get("packages")
        if isinstance(packages, dict):
            return list(packages.values())
        return cast(List[Dict[str, Any]], packages) if isinstance(packages, list) else []

    def get_shipping(self) -> Optional[Dict[str, Any]]:
        """Get the cart's whole ``shipping`` field: ``total_packages``,
        ``show_package_details``, ``has_calculated_shipping`` and ``packages``
        (keyed by package ID). ``None`` when the response has none.
        """
        shipping = self.get("shipping")
        return cast(Dict[str, Any], shipping) if isinstance(shipping, dict) else None

    def get_fees(self) -> List[Dict[str, Any]]:
        """Get cart fees from response data, as a list.

        The cart keys fees by fee ID (``{}`` when there are none; ``[]`` from
        CoCart 4.x).
        """
        fees = self.get("fees", [])
        if isinstance(fees, dict):
            return list(fees.values())
        return cast(List[Dict[str, Any]], fees) if isinstance(fees, list) else []

    def get_extensions(self) -> Dict[str, Any]:
        """Get the cart's ``extensions``: data plugins add to the cart, such as
        subscription ``recurring_totals`` (see ``docs/extension-data.md``).
        ``{}`` when there is none.
        """
        extensions = self.get("extensions", {})
        return cast(Dict[str, Any], extensions) if isinstance(extensions, dict) else {}

    def get_cross_sells(self) -> List[Dict[str, Any]]:
        """Get cross-sell products from response data."""
        return cast(List[Dict[str, Any]], self.get("cross_sells", []))

    def get_taxes(self) -> List[Dict[str, Any]]:
        """Get cart tax lines from response data, normalized to a flat list.

        The ``taxes`` field is returned as an array by some CoCart versions,
        but as a legacy object keyed by tax rate code by others, e.g.
        ``{"US-US-1": {"name": ..., "price": ...}}``. This normalizes both
        shapes to ``[{"key": ..., "name": ..., "price": ...}, ...]`` so
        callers never need to branch on plugin/version themselves.
        """
        raw = self.get("taxes", [])

        if isinstance(raw, list):
            return cast(List[Dict[str, Any]], raw)

        if isinstance(raw, dict):
            return [
                {
                    "key": key,
                    "name": tax.get("name") if isinstance(tax, dict) else None,
                    "price": tax.get("price") if isinstance(tax, dict) else None,
                }
                for key, tax in raw.items()
            ]

        return []

    def has_taxes(self) -> bool:
        """Check if the cart has any tax lines."""
        return len(self.get_taxes()) > 0

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

    def get_rate_limit(self) -> Dict[str, Optional[int]]:
        """The ``RateLimit-*`` headers (CoCart Plus, when rate limiting is on).

        Returns ``limit``, ``remaining``, ``reset`` (Unix time the window
        resets) and ``retry_after`` (seconds to wait after a 429); each is
        ``None`` when the header wasn't sent.
        """

        def number(name: str) -> Optional[int]:
            value = self.get_header(name)
            if value is None:
                return None
            try:
                return int(float(value))
            except (ValueError, OverflowError):
                return None

        return {
            "limit": number("RateLimit-Limit"),
            "remaining": number("RateLimit-Remaining"),
            "reset": number("RateLimit-Reset"),
            "retry_after": number("RateLimit-Retry-After"),
        }

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
