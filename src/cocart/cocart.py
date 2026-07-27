from __future__ import annotations

import json
import logging
import random
import threading
import time
from base64 import b64encode
from typing import Any, Callable, Dict, List, Optional, Set, cast
from urllib.parse import urlencode

from cocart.exceptions.authentication_exception import AuthenticationException
from cocart.exceptions.cocart_exception import CoCartException
from cocart.exceptions.two_factor_required_exception import TwoFactorRequiredException
from cocart.exceptions.validation_exception import ValidationException
from cocart.exceptions.version_exception import VersionException
from cocart.http.requests_adapter import RequestsAdapter
from cocart.response import Response
from cocart.storage.memory_storage import MemoryStorage

logger = logging.getLogger("cocart")


class _InFlightGet:
    """Tracks a GET request shared by concurrent callers requesting the same URL."""

    __slots__ = ("event", "response", "error")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.response: Optional[Response] = None
        self.error: Optional[BaseException] = None


class CoCart:
    """CoCart Python SDK.

    A Python SDK for interacting with the CoCart REST API.
    Supports guest customers (via cart_key) and authenticated users
    (via Basic Auth or JWT).

    Example::

        client = CoCart("https://example.com")
        response = client.products().all()
        print(response.to_dict())
    """

    VERSION = "1.0.0"
    API_VERSION = "v2"

    def __init__(self, store_url: str, **kwargs: Any) -> None:
        self._store_url = store_url.rstrip("/")
        self._rest_prefix: str = kwargs.get("rest_prefix", "wp-json").strip("/")
        self._namespace: str = kwargs.get("namespace", "cocart").strip("/")
        self._storage_key: str = kwargs.get("storage_key", "cocart_cart_key")
        self._cart_key: Optional[str] = kwargs.get("cart_key")
        self._auth: Optional[Dict[str, str]] = None
        self._jwt_token: Optional[str] = kwargs.get("jwt_token")
        self._refresh_token: Optional[str] = kwargs.get("jwt_refresh_token")
        self._consumer_key: Optional[str] = None
        self._consumer_secret: Optional[str] = None
        self._max_retries: int = max(0, kwargs.get("max_retries", 0))
        self._timeout: float = kwargs.get("timeout", 30.0)
        self._custom_headers: Dict[str, str] = dict(kwargs.get("headers") or {})
        self._storage = kwargs.get("storage") or MemoryStorage()
        self._debug: bool = kwargs.get("debug", False)
        self._auth_header_name: str = kwargs.get("auth_header_name", "Authorization")
        self._response_transformer: Optional[Callable[[Response], Response]] = None
        self._etag_enabled: bool = kwargs.get("etag", True)
        self._etag_cache: Dict[str, Dict[str, Any]] = {}
        self._main_plugin: str = kwargs.get("main_plugin", "basic")
        self._verify_ssl: bool = kwargs.get("verify_ssl", True)
        self._last_response: Optional[Response] = None

        # Event listeners
        self._listeners: Dict[str, Set[Any]] = {}

        # HTTP adapter
        self._http_adapter = RequestsAdapter()

        # In-flight GET de-duplication
        self._inflight_lock = threading.Lock()
        self._inflight_gets: Dict[str, _InFlightGet] = {}

        # Lazy-loaded instances
        self._jwt_manager_instance: Any = None
        self._cart_instance: Any = None
        self._products_instance: Any = None
        self._store_instance: Any = None
        self._sessions_instance: Any = None
        self._account_instance: Any = None

        # Handle auth kwargs
        username = kwargs.get("username")
        password = kwargs.get("password")
        if username and password:
            self._auth = {"username": username, "password": password}

        consumer_key = kwargs.get("consumer_key")
        consumer_secret = kwargs.get("consumer_secret")
        if consumer_key and consumer_secret:
            self._consumer_key = consumer_key
            self._consumer_secret = consumer_secret

    @staticmethod
    def create(store_url: str) -> CoCart:
        """Factory method for creating a new instance."""
        return CoCart(store_url)

    # --- Cart key ---

    def set_cart_key(self, cart_key: str) -> CoCart:
        self._cart_key = cart_key
        return self

    def get_cart_key(self) -> Optional[str]:
        return self._cart_key

    # --- Authentication ---

    def set_auth(self, username: str, password: str) -> CoCart:
        self._auth = {"username": username, "password": password}
        self._jwt_token = None
        return self

    def set_jwt_token(self, token: str) -> CoCart:
        self._jwt_token = token
        self._auth = None
        return self

    def get_jwt_token(self) -> Optional[str]:
        return self._jwt_token

    def set_refresh_token(self, token: str) -> CoCart:
        self._refresh_token = token
        return self

    def get_refresh_token(self) -> Optional[str]:
        return self._refresh_token

    def has_jwt_token(self) -> bool:
        return self._jwt_token is not None and self._jwt_token != ""

    def clear_jwt_token(self) -> CoCart:
        self._jwt_token = None
        self._refresh_token = None
        return self

    def set_woocommerce_credentials(self, key: str, secret: str) -> CoCart:
        self._consumer_key = key
        self._consumer_secret = secret
        return self

    def login(self, username: str, password: str) -> Response:
        """Login with username and password via JWT authentication.

        Raises :class:`~cocart.exceptions.TwoFactorRequiredException` if the
        CoCart 2FA plugin requires a verification code — catch it and call
        :meth:`verify_two_factor` to complete login.
        """
        result: Response = self.jwt().login(username, password)
        return result

    def verify_two_factor(
        self, username: str, password: str, code: str, provider: Optional[str] = None
    ) -> Response:
        """Complete login after a 2FA challenge from :meth:`login`."""
        result: Response = self.jwt().verify_two_factor(username, password, code, provider)
        return result

    def logout(self) -> CoCart:
        """Logout — call server logout endpoint, then clear local JWT tokens."""
        try:
            self.post("logout")
        except CoCartException:
            pass
        self.jwt().clear_tokens()
        return self

    def is_authenticated(self) -> bool:
        return self._auth is not None or (self._jwt_token is not None and self._jwt_token != "")

    def is_guest(self) -> bool:
        return not self.is_authenticated()

    def clear_session(self) -> CoCart:
        """Clear authentication and cart key."""
        self._auth = None
        self._jwt_token = None
        self._refresh_token = None
        self._cart_key = None
        self._storage.delete(self._storage_key)
        return self

    def transfer_cart_to_customer(self, username: str, password: str) -> Response:
        """Transfer cart from guest to authenticated user."""
        guest_cart_key = self._cart_key
        self.set_auth(username, password)
        if guest_cart_key:
            result: Response = self.cart().get(params={"cart_key": guest_cart_key})
            return result
        result2: Response = self.cart().get()
        return result2

    # --- Configuration ---

    def set_timeout(self, timeout: float) -> CoCart:
        self._timeout = timeout
        return self

    def set_max_retries(self, retries: int) -> CoCart:
        self._max_retries = max(0, retries)
        return self

    def set_rest_prefix(self, prefix: str) -> CoCart:
        self._rest_prefix = prefix.strip("/")
        return self

    def get_rest_prefix(self) -> str:
        return self._rest_prefix

    def set_namespace(self, namespace: str) -> CoCart:
        self._namespace = namespace.strip("/")
        return self

    def get_namespace(self) -> str:
        return self._namespace

    def add_header(self, name: str, value: str) -> CoCart:
        self._custom_headers[name] = value
        return self

    def set_storage(self, storage: Any) -> CoCart:
        self._storage = storage
        return self

    def get_storage(self) -> Any:
        return self._storage

    def set_debug(self, enabled: bool) -> CoCart:
        self._debug = enabled
        return self

    def set_auth_header_name(self, name: str) -> CoCart:
        self._auth_header_name = name
        return self

    def set_etag(self, enabled: bool) -> CoCart:
        self._etag_enabled = enabled
        return self

    def clear_etag_cache(self) -> CoCart:
        self._etag_cache.clear()
        return self

    def get_main_plugin(self) -> str:
        return self._main_plugin

    def set_main_plugin(self, plugin: str) -> CoCart:
        self._main_plugin = plugin
        return self

    def requires_basic(self, method: str) -> None:
        """Guard that raises if a method requires CoCart Starter but the SDK is configured for legacy."""
        if self._main_plugin == "legacy":
            raise VersionException(method)

    def set_verify_ssl(self, verify: bool) -> CoCart:
        self._verify_ssl = verify
        return self

    def set_response_transformer(self, fn: Optional[Callable[[Response], Response]]) -> CoCart:
        self._response_transformer = fn
        return self

    # --- Events ---

    def on(self, event: str, listener: Any) -> CoCart:
        """Register an event listener.

        Supported events: ``request``, ``response``, ``error``, ``retry``, ``auth:refresh``.
        """
        if event not in self._listeners:
            self._listeners[event] = set()
        self._listeners[event].add(listener)
        return self

    def off(self, event: str, listener: Any) -> CoCart:
        """Remove an event listener."""
        if event in self._listeners:
            self._listeners[event].discard(listener)
        return self

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        if self._debug:
            self._log_debug(event, data)
        for listener in self._listeners.get(event, set()):
            try:
                listener(data)
            except Exception:
                pass

    def _log_debug(self, event: str, data: Dict[str, Any]) -> None:
        prefix = "[CoCart]"
        if event == "request":
            logger.debug("%s %s %s", prefix, data.get("method"), data.get("url"))
        elif event == "response":
            logger.debug(
                "%s %s %s -> %s (%.0fms)",
                prefix,
                data.get("method"),
                data.get("url"),
                data.get("status"),
                data.get("duration", 0) * 1000,
            )
        elif event == "error":
            logger.debug("%s %s %s -> Error: %s", prefix, data.get("method"), data.get("url"), data.get("error"))
        elif event == "retry":
            logger.debug(
                "%s Retry %s/%s after %.0fms (%s)",
                prefix,
                data.get("attempt"),
                data.get("max_retries"),
                data.get("delay", 0) * 1000,
                data.get("reason"),
            )
        elif event == "auth:refresh":
            logger.debug("%s JWT token refresh %s", prefix, "succeeded" if data.get("success") else "failed")

    # --- Auth convenience ---

    def jwt(self) -> Any:
        """Get or create the JWT Manager instance."""
        if self._jwt_manager_instance is None:
            from cocart.jwt_manager import JwtManager

            self._jwt_manager_instance = JwtManager(self, self._storage, auto_refresh=True)
        return self._jwt_manager_instance

    def restore_session(self) -> None:
        """Restore the cart key from storage."""
        if self._cart_key is None:
            stored = self._storage.get(self._storage_key)
            if stored:
                self._cart_key = stored

    # --- Endpoints (lazy-loaded) ---

    def cart(self) -> Any:
        if self._cart_instance is None:
            from cocart.endpoints.cart import Cart

            self._cart_instance = Cart(self)
        return self._cart_instance

    def products(self) -> Any:
        if self._products_instance is None:
            from cocart.endpoints.products import Products

            self._products_instance = Products(self)
        return self._products_instance

    def store(self) -> Any:
        if self._store_instance is None:
            from cocart.endpoints.store import Store

            self._store_instance = Store(self)
        return self._store_instance

    def sessions(self) -> Any:
        if self._sessions_instance is None:
            from cocart.endpoints.sessions import Sessions

            self._sessions_instance = Sessions(self)
        return self._sessions_instance

    def account(self) -> Any:
        if self._account_instance is None:
            from cocart.endpoints.account import Account

            self._account_instance = Account(self)
        return self._account_instance

    # --- Batch ---

    def batch(self, requests: List[Dict[str, Any]]) -> Response:
        """Dispatch multiple sub-requests in a single call via ``{namespace}/batch``.

        Requires the CoCart Plus plugin. Returns one merged, up-to-date cart
        response with per-operation notices, instead of one response per request.

        Args:
            requests: A list of ``{method, path, body?}`` request items.
        """
        if not requests:
            raise ValidationException(
                "batch() requires at least one request.",
                http_code=0,
                error_code="cocart_batch_empty",
            )

        params = {"cart_key": self._cart_key} if self._cart_key and not self.is_authenticated() else None

        try:
            return self.request_raw("POST", f"{self._namespace}/batch", params, {"requests": requests})
        except CoCartException as e:
            if e.error_code == "rest_no_route":
                raise CoCartException(
                    "This method is only available with another CoCart plugin. "
                    "Please ask support for assistance!",
                    http_code=404,
                    error_code="cocart_plugin_required",
                ) from e
            raise

    # --- HTTP methods ---

    def get(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Response:
        return self.request("GET", endpoint, params)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        return self.request("POST", endpoint, params, data)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        return self.request("PUT", endpoint, params, data)

    def delete(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Response:
        return self.request("DELETE", endpoint, params)

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Make an HTTP request to the API.

        If a JwtManager with auto-refresh is attached and the request fails
        with an authentication error, the token is refreshed and retried once.
        """
        try:
            return self._execute_request(method, endpoint, params, data)
        except AuthenticationException as e:
            if (
                not isinstance(e, TwoFactorRequiredException)
                and self._jwt_manager_instance is not None
                and self._jwt_manager_instance.is_auto_refresh_enabled()
                and self._refresh_token is not None
            ):
                try:
                    self._jwt_manager_instance.refresh()
                    self._emit("auth:refresh", {"success": True})
                    return self._execute_request(method, endpoint, params, data)
                except Exception:
                    self._emit("auth:refresh", {"success": False})
                    raise e
            raise

    def request_raw(
        self,
        method: str,
        route: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Make an HTTP request using a full REST route (relative to wp-json/).

        Does NOT prepend the namespace/version prefix.
        """
        url = f"{self._store_url}/{self._rest_prefix}/{route.lstrip('/')}"

        if params:
            url += "?" + urlencode(params)

        headers = self._build_headers()
        body = json.dumps(data) if data else None

        http_resp = self._http_adapter.request(
            method=method,
            url=url,
            headers=headers,
            body=body,
            timeout=self._timeout,
            verify_ssl=self._verify_ssl,
        )

        self._last_response = Response(http_resp.status_code, http_resp.headers, http_resp.body)
        self._extract_cart_key(self._last_response)

        if http_resp.status_code >= 400:
            self._handle_error_response(self._last_response)

        return self._apply_transformer(self._last_response)

    def get_last_response(self) -> Optional[Response]:
        return self._last_response

    def get_store_url(self) -> str:
        return self._store_url

    # --- Internal ---

    def _execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        url = self._build_url(endpoint, params)

        if method != "GET":
            return self._perform_request(method, url, data)

        # De-duplicate identical concurrent GETs (e.g. multiple threads
        # requesting the same listing at once) so they share one network
        # request instead of firing one each.
        with self._inflight_lock:
            inflight = self._inflight_gets.get(url)
            is_leader = inflight is None
            if is_leader:
                inflight = _InFlightGet()
                self._inflight_gets[url] = inflight

        assert inflight is not None
        if not is_leader:
            inflight.event.wait()
            if inflight.error is not None:
                raise inflight.error
            return cast(Response, inflight.response)

        try:
            response = self._perform_request(method, url, data)
            inflight.response = response
            return response
        except BaseException as e:
            inflight.error = e
            raise
        finally:
            with self._inflight_lock:
                self._inflight_gets.pop(url, None)
            inflight.event.set()

    def _perform_request(self, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Response:
        headers = self._build_headers()
        body = json.dumps(data) if data else None

        # ETag: add If-None-Match for GET requests
        if method == "GET" and self._etag_enabled:
            cached = self._etag_cache.get(url)
            if cached:
                headers["If-None-Match"] = cached["etag"]

        self._emit("request", {"method": method, "url": url, "headers": headers, "body": body})

        attempt = 0
        start_time = time.monotonic()

        while True:
            try:
                http_resp = self._http_adapter.request(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout=self._timeout,
                    verify_ssl=self._verify_ssl,
                )
            except CoCartException as e:
                if attempt < self._max_retries and self._is_transient_error(e):
                    attempt += 1
                    delay = self._get_retry_delay(attempt)
                    self._emit("retry", {
                        "method": method, "url": url, "attempt": attempt,
                        "max_retries": self._max_retries, "delay": delay, "reason": "transient_error",
                    })
                    time.sleep(delay)
                    continue
                self._emit("error", {"method": method, "url": url, "error": e})
                raise
            except Exception as e:
                error = CoCartException(str(e), http_code=0, error_code="network_error")
                self._emit("error", {"method": method, "url": url, "error": error})
                raise error from e

            duration = time.monotonic() - start_time

            # A 304 has no body — reuse the body/headers cached alongside the
            # ETag that produced the match, so callers still get the actual
            # data instead of an empty response. Falls back to the live
            # (empty) response if we somehow have no cache entry for this URL.
            is_not_modified = method == "GET" and self._etag_enabled and http_resp.status_code == 304
            cached_entry = self._etag_cache.get(url) if is_not_modified else None

            self._last_response = Response(
                http_resp.status_code,
                cached_entry["headers"] if cached_entry else http_resp.headers,
                cached_entry["body"] if cached_entry else http_resp.body,
            )
            self._extract_cart_key(self._last_response)

            # ETag: cache the ETag + body from a fresh (non-304) response
            if method == "GET" and self._etag_enabled and not is_not_modified:
                etag = self._last_response.get_etag()
                if etag:
                    self._etag_cache[url] = {
                        "etag": etag,
                        "body": http_resp.body,
                        "headers": http_resp.headers,
                    }

            # Retry on transient HTTP status codes (429, 503)
            if attempt < self._max_retries and self._is_retryable_status(http_resp.status_code):
                attempt += 1
                delay = self._get_retry_delay(attempt, self._last_response)
                self._emit("retry", {
                    "method": method, "url": url, "attempt": attempt,
                    "max_retries": self._max_retries, "delay": delay,
                    "reason": f"http_{http_resp.status_code}",
                })
                time.sleep(delay)
                continue

            if http_resp.status_code >= 400:
                self._emit("response", {
                    "method": method, "url": url, "status": http_resp.status_code, "duration": duration,
                })
                self._handle_error_response(self._last_response, method, url)

            self._emit("response", {
                "method": method, "url": url, "status": http_resp.status_code, "duration": duration,
            })
            return self._apply_transformer(self._last_response)

    def _build_url(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> str:
        resolved_params = dict(params or {})

        # Add cart_key if set and not authenticated
        if self._cart_key and not self.is_authenticated():
            resolved_params["cart_key"] = self._cart_key

        # Normalize field filtering parameter based on main plugin
        if self._main_plugin == "legacy":
            if "_fields" in resolved_params and "fields" not in resolved_params:
                resolved_params["fields"] = resolved_params.pop("_fields")
        else:
            if "fields" in resolved_params and "_fields" not in resolved_params:
                resolved_params["_fields"] = resolved_params.pop("fields")

        url = f"{self._store_url}/{self._rest_prefix}/{self._namespace}/{self.API_VERSION}/{endpoint.lstrip('/')}"

        if resolved_params:
            url += "?" + urlencode(resolved_params)

        return url

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"CoCart-Python-SDK/{self.VERSION}",
        }

        # Authentication
        if self._jwt_token:
            headers[self._auth_header_name] = f"Bearer {self._jwt_token}"
        elif self._auth:
            creds = f"{self._auth['username']}:{self._auth['password']}"
            encoded = b64encode(creds.encode()).decode()
            headers[self._auth_header_name] = f"Basic {encoded}"
        elif self._consumer_key and self._consumer_secret:
            creds = f"{self._consumer_key}:{self._consumer_secret}"
            encoded = b64encode(creds.encode()).decode()
            headers[self._auth_header_name] = f"Basic {encoded}"

        # Cart key header — send only the header name the configured plugin
        # actually allows (mixing both breaks CORS preflight on real installs).
        if self._cart_key and not self.is_authenticated():
            cart_key_header = "CoCart-API-Cart-Key" if self._main_plugin == "legacy" else "Cart-Key"
            headers[cart_key_header] = self._cart_key

        headers.update(self._custom_headers)
        return headers

    def _extract_cart_key(self, response: Response) -> None:
        cart_key = response.get_header("Cart-Key") or response.get_header("CoCart-API-Cart-Key")
        if cart_key is not None:
            self._cart_key = cart_key
            self._storage.set(self._storage_key, cart_key)

    def _handle_error_response(
        self,
        response: Response,
        method: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        data = response.to_dict()
        code = data.get("code", "unknown_error") if isinstance(data, dict) else "unknown_error"
        api_message = data.get("message", "An unknown error occurred") if isinstance(data, dict) else "An unknown error occurred"
        http_code = response.status_code

        context = f"{method} {url}: " if method and url else ""
        code_label = f" [{code}]" if code != "unknown_error" else ""
        message = f"{context}{api_message}{code_label}"

        response_data = data if isinstance(data, dict) else {}

        # 2FA challenge (must be checked before generic authentication handling)
        if code == "cocart_2fa_required":
            raise TwoFactorRequiredException(message, http_code, code, response_data)

        # Authentication errors
        if http_code in (401, 403) or (isinstance(code, str) and "authenticat" in code):
            raise AuthenticationException(message, http_code, code, response_data)

        # Validation errors
        if http_code == 400 or (isinstance(code, str) and ("invalid" in code or "missing" in code)):
            raise ValidationException(message, http_code, code, response_data)

        raise CoCartException(message, http_code, code, response_data)

    def _is_transient_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        return "timeout" in msg or "timed out" in msg or "connection" in msg

    def _is_retryable_status(self, status: int) -> bool:
        return status in (429, 503)

    def _get_retry_delay(self, attempt: int, response: Optional[Response] = None) -> float:
        if response:
            retry_after = response.get_header("Retry-After")
            if retry_after is not None:
                try:
                    return min(float(retry_after), 60.0)
                except ValueError:
                    pass
        base = float(min(2 ** (attempt - 1), 30.0))
        # ±20% jitter so many clients retrying at once don't re-collide on the
        # same schedule (avoids synchronized retry storms against a rate limit).
        jitter = 0.8 + random.random() * 0.4
        return base * jitter

    def _apply_transformer(self, response: Response) -> Response:
        if self._response_transformer:
            return self._response_transformer(response)
        return response
