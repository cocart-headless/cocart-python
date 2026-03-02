from __future__ import annotations

from typing import Dict, Optional

from cocart.endpoints.endpoint import Endpoint
from cocart.response import Response


class Store(Endpoint):
    """Store Endpoint — get store information."""

    _endpoint = "store"

    def info(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get store information (currency, timezone, configuration)."""
        return self._get("", params)
