from __future__ import annotations

from typing import Any, Dict, Optional

from cocart.endpoints.endpoint import Endpoint
from cocart.exceptions.cocart_exception import CoCartException
from cocart.response import Response


class Account(Endpoint):
    """Account endpoint — handles all cocart/v2/my-account API operations."""

    _endpoint = ""  # all calls use raw routing

    _BASE = "cocart/v2/my-account"

    def _raw_path(self, sub: str = "") -> str:
        if not sub:
            return self._BASE
        return self._BASE + "/" + sub.lstrip("/")

    def _get_raw(
        self,
        sub: str = "",
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        try:
            return self._client.request_raw("GET", self._raw_path(sub), params)
        except CoCartException as e:
            self._handle_no_route(e)

    def _post_raw(
        self,
        sub: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        try:
            return self._client.request_raw("POST", self._raw_path(sub), None, data)
        except CoCartException as e:
            self._handle_no_route(e)

    # --- Profile ---

    def get_profile(self) -> Response:
        """Return the authenticated user's account profile."""
        return self._get_raw()

    def update_profile(self, data: Dict[str, Any]) -> Response:
        """Update the authenticated user's profile."""
        return self._post_raw("", data)

    def change_password(self, current: str, password: str, confirm: str) -> Response:
        """Change the authenticated user's password.

        Field names are remapped to the wire format:
        current → password_current, password → password_1, confirm → password_2.
        """
        return self._post_raw("change-password", {
            "password_current": current,
            "password_1": password,
            "password_2": confirm,
        })

    # --- Orders ---

    def get_orders(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Return a paginated list of the user's orders."""
        return self._get_raw("orders", params)

    def get_order(self, order_id: int) -> Response:
        """Return a single order by ID."""
        return self._get_raw(f"orders/{order_id}")

    def get_guest_order(self, order_id: int, email: str) -> Response:
        """Return a single guest order by ID and billing email."""
        return self._get_raw(f"orders/{order_id}", {"email": email})

    # --- Downloads ---

    def get_order_downloads(self, order_id: int) -> Response:
        """Return downloadable files for a specific order."""
        return self._get_raw(f"orders/{order_id}/downloads")

    def get_guest_order_downloads(self, order_id: int, email: str) -> Response:
        """Return downloadable files for a specific guest order."""
        return self._get_raw(f"orders/{order_id}/downloads", {"email": email})

    def get_downloads(self) -> Response:
        """Return all downloadable files available to the authenticated user."""
        return self._get_raw("downloads")

    # --- Reviews ---

    def get_reviews(self) -> Response:
        """Return the authenticated user's product reviews."""
        return self._get_raw("reviews")
