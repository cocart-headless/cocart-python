from __future__ import annotations

from typing import Any, Dict, Optional

from cocart.checkout_result import CheckoutResult, to_payment_data_pairs
from cocart.endpoints.endpoint import Endpoint, document_query
from cocart.exceptions.cocart_exception import CoCartException
from cocart.response import Response

ROUTE_BASE = "cocart/v2/my-account"
REGISTER_ROUTE = "cocart/v2/register"
WITHDRAWAL_ROUTE = "cocart/v2/order-withdrawal"


class Account(Endpoint):
    """Account Endpoint — handles the authenticated customer's account data.

    Provides access to profile, address, orders, downloads, subscriptions and
    email verification (CoCart Plus) via the fixed ``cocart/v2/my-account``
    route (bypassing the configured namespace/version, since this route isn't
    namespaced like Cart/Products/Store/Sessions).

    All methods require the customer to be authenticated (Basic Auth or JWT),
    except :meth:`register`, :meth:`get_guest_order`,
    :meth:`get_guest_order_downloads` and :meth:`request_order_withdrawal`.
    If the required CoCart plugin isn't installed, a ``cocart_plugin_required``
    error is raised via the inherited ``_handle_no_route`` fail-safe.
    """

    _endpoint = ""

    # --- Helpers ---

    def _raw_path(self, sub: str = "") -> str:
        if not sub:
            return ROUTE_BASE
        return f"{ROUTE_BASE}/{sub.lstrip('/')}"

    def _raw(
        self,
        method: str,
        route: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        try:
            return self._client.request_raw(method, route, params, data)
        except CoCartException as e:
            self._handle_no_route(e)

    def _get_raw(self, sub: str = "", params: Optional[Dict[str, str]] = None) -> Response:
        return self._raw("GET", self._raw_path(sub), params)

    def _post_raw(self, sub: str = "", data: Optional[Dict[str, Any]] = None) -> Response:
        return self._raw("POST", self._raw_path(sub), None, data)

    # --- Registration (CoCart Plus) ---

    def register(
        self,
        email: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Response:
        """Register a new customer. Doesn't need the customer logged in.

        The username and password are sent as ``requested_username`` and
        ``requested_password``: CoCart treats non-empty ``username`` and
        ``password`` fields as a Basic Auth attempt.

        Args:
            email: The customer's email.
            username: Optional if the store generates usernames from the email.
            password: Optional if the store generates passwords.
        """
        data: Dict[str, Any] = {"email": email}
        if username is not None:
            data["requested_username"] = username
        if password is not None:
            data["requested_password"] = password
        return self._raw("POST", REGISTER_ROUTE, None, data)

    # --- Profile ---

    def get_profile(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """The signed-in customer: name, email, addresses and order stats.

        Args:
            params: Optional ``formatted`` (amounts formatted for display) and
                ``meta_keys`` (only these keys in ``meta``; a list is comma-joined).
        """
        return self._get_raw("", document_query(params))

    def update_profile(self, data: Dict[str, Any]) -> Response:
        """Save the account details: send only what changes.

        Returns the customer with ``account_updated`` in ``result``. Every
        field at fault is reported at once (:meth:`CoCartException.get_fields`).

        Args:
            data: Profile fields (e.g. ``account_first_name``,
                ``account_last_name``, ``account_display_name``, ``account_email``).
        """
        return self._post_raw("", data)

    def change_password(self, current: str, password: str, confirm: str) -> Response:
        """Change the authenticated user's password (``POST /my-account``).

        Returns the customer with ``account_updated`` in ``result``. A wrong
        current password is a :class:`ValidationException`
        (``cocart_account_incorrect_current_password``).

        Args:
            current: Current password.
            password: New password.
            confirm: Confirm the new password.
        """
        return self._post_raw("", {
            "password_current": current,
            "password_1": password,
            "password_2": confirm,
        })

    def update_address(self, data: Dict[str, Any]) -> Response:
        """Update the customer's saved billing and/or shipping address.

        Args:
            data: ``billing_address`` and/or ``shipping_address``, each with
                unprefixed fields (``first_name``, ``address_1``…).
        """
        return self._post_raw("address", data)

    # --- Orders ---

    def get_orders(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """The customer's orders, newest first, with ``pagination`` (also in the
        ``X-WP-Total`` and ``X-WP-TotalPages`` headers).

        Args:
            params: Optional ``page``, ``per_page``, ``order`` (``asc`` or
                ``desc``), ``status`` (one or a list, comma-joined), ``after``
                and ``before`` (ISO 8601 dates), ``subscription_order_type``
                (``parent``, ``renewal``, ``switch`` or ``resubscribe``),
                ``formatted`` and ``meta_keys``.
        """
        return self._get_raw("orders", document_query(params))

    def get_order(self, order_id: int, params: Optional[Dict[str, Any]] = None) -> Response:
        """One of the customer's orders. Someone else's order is ``404 cocart_order_not_found``.

        Args:
            params: Optional ``formatted`` and ``meta_keys``.
        """
        return self._get_raw(f"orders/{order_id}", document_query(params))

    def get_guest_order(self, order_id: int, email: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """A guest's order, looked up with its billing email.

        It comes without its ``key``. Lookups are rate limited
        (``429 cocart_guest_lookup_rate_limited``).

        Args:
            order_id: Order ID.
            email: Billing email used when placing the order.
            params: Optional ``formatted`` and ``meta_keys``.
        """
        return self._get_raw(f"orders/{order_id}", document_query({**(params or {}), "email": email}))

    def cancel_order(self, order_id: int) -> Response:
        """Cancel one of the customer's orders where WooCommerce allows it
        (for example a pending or failed order).
        """
        return self._post_raw(f"orders/{order_id}/cancel")

    # --- Downloads ---

    def get_order_downloads(self, order_id: int) -> Response:
        """The files one of the customer's orders can download, as a list (``to_dict()`` returns it)."""
        return self._get_raw(f"orders/{order_id}/downloads")

    def get_guest_order_downloads(self, order_id: int, email: str) -> Response:
        """The files a guest's order can download, looked up with its billing
        email, as a list.

        Args:
            order_id: Order ID.
            email: Billing email used when placing the order.
        """
        return self._get_raw(f"orders/{order_id}/downloads", {"email": email})

    def get_downloads(self) -> Response:
        """Every file the customer can download, as a list (``to_dict()`` returns it)."""
        return self._get_raw("downloads")

    # --- Reviews ---

    def get_reviews(self, params: Optional[Dict[str, str]] = None) -> Response:
        """The customer's product reviews (``GET /products/reviews/mine``).
        Same as ``products().my_reviews()``.
        """
        result: Response = self._client.products().my_reviews(params)
        return result

    # --- Email verification (CoCart Plus) ---

    def verify_email(self, key: str, user_id: int) -> Response:
        """Confirm a pending email change, with the key and user ID from the emailed link."""
        return self._get_raw("verify-email", {"key": key, "user_id": str(user_id)})

    def send_order_email_verification(self) -> Response:
        """Email the customer a link proving they own the account email, so
        WooCommerce links their past guest orders to it (WooCommerce 11+).
        The response's ``status`` is ``sent``, or ``throttled`` (once a minute).
        """
        return self._post_raw("verify-order-email")

    def verify_order_email(self, key: str, user_id: int) -> Response:
        """Verify the email with the key from :meth:`send_order_email_verification`'s email."""
        return self._get_raw("verify-order-email", {"key": key, "user_id": str(user_id)})

    # --- Subscriptions (CoCart Plus with WooCommerce Subscriptions) ---

    def get_subscriptions(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """The customer's subscriptions, with ``pagination``.

        Args:
            params: Optional ``page``, ``per_page``, ``order`` (``asc`` or
                ``desc``), ``status`` (one or a list, comma-joined),
                ``formatted`` and ``meta_keys``.
        """
        return self._get_raw("subscriptions", document_query(params))

    def get_subscription(
        self,
        subscription_id: int,
        email: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """One subscription. Pass ``email`` to view it as a guest.

        Args:
            params: Optional ``formatted`` and ``meta_keys``.
        """
        query: Dict[str, Any] = dict(params or {})
        if email:
            query["email"] = email
        return self._get_raw(f"subscriptions/{subscription_id}", document_query(query))

    def suspend_subscription(self, subscription_id: int) -> Response:
        """Suspend (put on hold) a subscription."""
        return self._post_raw(f"subscriptions/{subscription_id}/suspend")

    def cancel_subscription(self, subscription_id: int) -> Response:
        """Cancel a subscription."""
        return self._post_raw(f"subscriptions/{subscription_id}/cancel")

    def reactivate_subscription(self, subscription_id: int) -> Response:
        """Reactivate a suspended subscription."""
        return self._post_raw(f"subscriptions/{subscription_id}/reactivate")

    def set_subscription_auto_renew(self, subscription_id: int, enabled: bool) -> Response:
        """Turn automatic renewal on or off."""
        return self._post_raw(f"subscriptions/{subscription_id}/auto-renew", {"enabled": enabled})

    def update_subscription_payment_method(self, subscription_id: int, data: Dict[str, Any]) -> CheckoutResult:
        """Change the card a subscription renews with: a saved card or a new one.

        A new card may need 3D Secure, so this returns a :class:`CheckoutResult`,
        read as at checkout: ``is_complete()`` once changed
        (``payment_method_changed``, with ``subscription_id``); on
        ``needs_confirmation()``, confirm ``client_secret`` with the gateway's
        SDK and call again with the same input; on ``needs_redirect()``, send
        the customer to ``redirect_url``. A declined card is a failed result,
        not an exception. Another change still running is
        ``409 cocart_payment_in_progress``.

        Args:
            data: ``payment_method`` (gateway ID, e.g. ``stripe``), and
                ``token_id`` (a saved card's ID) or ``payment_data`` (a new
                card, e.g. ``{"wc-stripe-payment-method": "pm_…"}``).
        """
        body = dict(data)
        if isinstance(body.get("payment_data"), (dict, list)):
            body["payment_data"] = to_payment_data_pairs(body["payment_data"])
        return CheckoutResult.from_response(self._post_raw(f"subscriptions/{subscription_id}/payment-method", body))

    def resubscribe(self, subscription_id: int) -> Response:
        """Put an ended subscription's items in the cart to subscribe again
        (checkout follows as usual).
        """
        return self._post_raw(f"subscriptions/{subscription_id}/resubscribe")

    def cancel_resubscribe(self, subscription_id: int) -> Response:
        """Undo :meth:`resubscribe`: restore the cart as it was before."""
        return self._raw("DELETE", self._raw_path(f"subscriptions/{subscription_id}/resubscribe"))

    # --- Order withdrawal (CoCart Plus) ---

    def request_order_withdrawal(self, data: Dict[str, Any]) -> Response:
        """Submit an order withdrawal (right of withdrawal) request. Doesn't
        need the customer logged in.

        Args:
            data: ``first_name``, ``last_name``, ``email``,
                ``email_confirmation``, ``order_number``, and optionally
                ``withdrawal_type`` (``full_order`` or ``specific_items_only``)
                and ``additional_details`` (required for
                ``specific_items_only``).
        """
        return self._raw("POST", WITHDRAWAL_ROUTE, None, data)
