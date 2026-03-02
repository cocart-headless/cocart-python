from __future__ import annotations

from typing import Dict, Optional

from cocart.endpoints.endpoint import Endpoint
from cocart.response import Response


class Sessions(Endpoint):
    """Sessions Endpoint — handles cart session management for administrators.

    Requires WooCommerce REST API credentials (consumer_key/consumer_secret).

    Note: The list endpoint uses plural "sessions", while individual
    session operations use singular "session/{key}" to match the API.
    """

    _endpoint = "sessions"

    def all(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get all cart sessions."""
        return self._get("", params)

    def find(self, session_key: str, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a specific cart session."""
        return self._client.get("session/" + session_key, params)

    def destroy(self, session_key: str) -> Response:
        """Delete a cart session."""
        return self._client.delete("session/" + session_key)

    def get_items(self, session_key: str) -> Response:
        """Get session items."""
        return self._client.get("session/" + session_key + "/items")

    def by_session(self, customer_id: int) -> Response:
        """Get session by customer ID."""
        return self._client.get("session/" + str(customer_id))

    def destroy_session(self, customer_id: int) -> Response:
        """Delete session by customer ID."""
        return self._client.delete("session/" + str(customer_id))
