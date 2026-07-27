from __future__ import annotations

from typing import Any, Dict, Optional

from cocart.endpoints.endpoint import Endpoint
from cocart.exceptions.cocart_exception import CoCartException
from cocart.response import Response

ROUTE_BASE = "cocart/v2/my-account"


class Account(Endpoint):
    """Account Endpoint — handles the authenticated customer's account data.

    Provides access to profile, orders, downloads, and reviews via the fixed
    ``cocart/v2/my-account`` route (bypassing the configured namespace/version,
    since this route isn't namespaced like Cart/Products/Store/Sessions).

    All methods require the customer to be authenticated (Basic Auth or JWT).
    If the required CoCart plugin isn't installed, a ``cocart_plugin_required``
    error is raised via the inherited ``_handle_no_route`` fail-safe.
    """

    _endpoint = ""

    # --- Helpers ---

    def _raw_path(self, sub: str = "") -> str:
        if not sub:
            return ROUTE_BASE
        return f"{ROUTE_BASE}/{sub.lstrip('/')}"

    def _get_raw(self, sub: str = "", params: Optional[Dict[str, str]] = None) -> Response:
        try:
            return self._client.request_raw("GET", self._raw_path(sub), params)
        except CoCartException as e:
            self._handle_no_route(e)

    def _post_raw(self, sub: str = "", data: Optional[Dict[str, Any]] = None) -> Response:
        try:
            return self._client.request_raw("POST", self._raw_path(sub), None, data)
        except CoCartException as e:
            self._handle_no_route(e)

    # --- Profile ---

    def get_profile(self) -> Response:
        """Get the authenticated user's account profile."""
        return self._get_raw()

    def update_profile(self, data: Dict[str, Any]) -> Response:
        """Update the authenticated user's profile.

        Args:
            data: Profile fields (e.g. ``account_first_name``,
                ``account_last_name``, ``account_display_name``, ``account_email``).
        """
        return self._post_raw("", data)

    def change_password(self, current: str, password: str, confirm: str) -> Response:
        """Change the authenticated user's password.

        Args:
            current: Current password.
            password: New password.
            confirm: Confirm the new password.
        """
        return self._post_raw("change-password", {
            "password_current": current,
            "password_1": password,
            "password_2": confirm,
        })

    # --- Orders ---

    def get_orders(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get the user's order history.

        Args:
            params: Query params — ``page``, ``per_page``, ``order`` (ASC|DESC).
        """
        return self._get_raw("orders", params)

    def get_order(self, order_id: int) -> Response:
        """Get a single order by ID."""
        return self._get_raw(f"orders/{order_id}")

    def get_guest_order(self, order_id: int, email: str) -> Response:
        """Get a single guest order by ID and billing email.

        Args:
            order_id: Order ID.
            email: Billing email used when placing the order.
        """
        return self._get_raw(f"orders/{order_id}", {"email": email})

    # --- Downloads ---

    def get_order_downloads(self, order_id: int) -> Response:
        """Get downloadable files for a specific order."""
        return self._get_raw(f"orders/{order_id}/downloads")

    def get_guest_order_downloads(self, order_id: int, email: str) -> Response:
        """Get downloadable files for a specific guest order.

        Args:
            order_id: Order ID.
            email: Billing email used when placing the order.
        """
        return self._get_raw(f"orders/{order_id}/downloads", {"email": email})

    def get_downloads(self) -> Response:
        """Get all downloadable files available to the authenticated user."""
        return self._get_raw("downloads")

    # --- Reviews ---

    def get_reviews(self) -> Response:
        """Get the authenticated user's product reviews."""
        return self._get_raw("reviews")
