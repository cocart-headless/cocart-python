from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from cocart.exceptions.cocart_exception import CoCartException

if TYPE_CHECKING:
    from cocart.cocart import CoCart
    from cocart.response import Response


class Endpoint:
    """Abstract base class for all endpoint classes.

    Provides HTTP method helpers that prepend the endpoint prefix
    and handle ``rest_no_route`` errors with a friendly message.
    """

    _endpoint: str = ""

    def __init__(self, client: CoCart) -> None:
        self._client = client

    def _build_path(self, path: str = "") -> str:
        """Build the full endpoint path."""
        if not path:
            return self._endpoint
        return self._endpoint.rstrip("/") + "/" + path.lstrip("/")

    def _get(
        self,
        path: str = "",
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make a GET request."""
        try:
            return self._client.get(self._build_path(path), params)
        except CoCartException:
            raise
        except Exception as e:
            self._handle_no_route(e)

    def _post(
        self,
        path: str = "",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make a POST request."""
        try:
            return self._client.post(self._build_path(path), data, params)
        except CoCartException:
            raise
        except Exception as e:
            self._handle_no_route(e)

    def _put(
        self,
        path: str = "",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make a PUT request."""
        try:
            return self._client.put(self._build_path(path), data, params)
        except CoCartException:
            raise
        except Exception as e:
            self._handle_no_route(e)

    def _delete(
        self,
        path: str = "",
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make a DELETE request."""
        try:
            return self._client.delete(self._build_path(path), params)
        except CoCartException:
            raise
        except Exception as e:
            self._handle_no_route(e)

    def _handle_no_route(self, e: Exception) -> None:
        """Handle rest_no_route errors with a friendly message."""
        if isinstance(e, CoCartException) and e.error_code == "rest_no_route":
            raise CoCartException(
                "This method is only available with another CoCart plugin. "
                "Please ask support for assistance!",
                http_code=404,
                error_code="cocart_plugin_required",
            )
        raise e

    @staticmethod
    def _stringify_params(params: Dict[str, Any]) -> Dict[str, str]:
        """Convert typed params to ``Dict[str, str]`` for the HTTP layer."""
        result: Dict[str, str] = {}
        for key, value in params.items():
            if value is not None:
                result[key] = str(value)
        return result
