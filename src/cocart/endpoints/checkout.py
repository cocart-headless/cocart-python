from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import unquote_plus, urlsplit

from cocart.checkout_result import CheckoutResult, to_payment_data_pairs
from cocart.endpoints.endpoint import document_query
from cocart.exceptions.checkout_outcome_unknown_exception import CheckoutOutcomeUnknownException
from cocart.exceptions.cocart_exception import CoCartException
from cocart.exceptions.validation_exception import ValidationException
from cocart.response import Response

if TYPE_CHECKING:
    from cocart.cocart import CoCart

ROUTE = "cocart/v2/checkout"
API = "cocart/v2"

# A checkout_id CoCart Plus accepts: 16 to 64 letters, digits, "-" or "_".
_CHECKOUT_ID = re.compile(r"[A-Za-z0-9_-]{16,64}")


def _with_payment_data_pairs(data: Dict[str, Any]) -> Dict[str, Any]:
    body = dict(data)
    if isinstance(body.get("payment_data"), (dict, list)):
        body["payment_data"] = to_payment_data_pairs(body["payment_data"])
    return body


def _new_checkout_id() -> str:
    """A random ID for one checkout: ``chk_`` and 32 hex digits."""
    return "chk_" + secrets.token_hex(16)


def _is_lost_response(error: CoCartException) -> bool:
    """No answer came back: the connection dropped, it timed out, or a proxy gave up."""
    if error.http_code == 0:
        return error.error_code in ("network_error", "request_timeout")
    return error.http_code in (502, 504)


def _is_payment_in_progress(error: CoCartException) -> bool:
    """Another request is still taking payment for the same cart, so how this one ends isn't known yet."""
    return error.http_code == 409 and error.error_code == "cocart_payment_in_progress"


def _query_params(url: str) -> Dict[str, str]:
    """A URL's query parameters, decoded, with every value as a string."""
    params: Dict[str, str] = {}
    for part in urlsplit(url).query.split("&"):
        if not part:
            continue
        key, _, value = part.partition("=")
        params[unquote_plus(key)] = unquote_plus(value)
    return params


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


class Checkout:
    """Checkout Endpoint (CoCart Plus 2.0).

    Places orders and takes payment. Card details never reach this code: the
    browser turns them into a payment method ID with the gateway's own
    JavaScript, and the order is placed with that ID. ``payment_data`` only
    ever carries such gateway tokens, never card numbers.
    """

    def __init__(self, client: CoCart) -> None:
        self._client = client

    def get(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """The checkout as it stands, like a receipt: items, coupons, fees,
        ``totals`` and ``total_lines``, the payment method, the addresses, each
        shipping package with its rates, and ``actions``.

        Call it for the page the customer reviews before paying: CoCart Plus
        remembers the total it showed, and refuses the order if the total has
        changed by then (``409 cocart_checkout_total_mismatch``). Don't call it
        just before placing the order.

        Args:
            params: Optional ``currency`` (prices in this currency, on a
                multi-currency store), ``formatted`` (amounts formatted for
                display instead of minor units) and ``thumb`` (``False`` leaves
                each item's ``featured_image`` empty).
        """
        return self._client.request_raw("GET", ROUTE, document_query(params))

    def update(self, data: Dict[str, Any]) -> Response:
        """Save what the customer has entered so far, without placing the order.

        Addresses, the shipping method, the payment method, a coupon
        (``coupon_code`` with ``coupon_action`` ``apply`` or ``remove``) or the
        currency. Returns the checkout with what it did in ``result``:
        ``checkout_updated``, or ``checkout_partly_updated`` with what wasn't
        applied, and why, in ``result.not_applied`` (``[{field, code,
        message}]``). Every address field at fault is reported at once
        (:meth:`CoCartException.get_fields`).
        """
        return self._client.request_raw("PUT", ROUTE, data=data)

    def process(self, data: Dict[str, Any]) -> Response:
        """Create the order and attempt payment, sending ``payment_data`` as
        given (the low-level call behind :meth:`place_order`)."""
        return self._client.request_raw("POST", ROUTE, data=data)

    def place_order(self, data: Dict[str, Any]) -> CheckoutResult:
        """Create the order and take payment.

        ``payment_data`` is a dict of the keys the WooCommerce gateway reads,
        e.g. ``{"wc-stripe-payment-method": "pm_…"}``: gateway tokens only,
        never card numbers. A free order needs neither it nor
        ``payment_method``. Calling again for the same cart lands on the same
        order. A declined card is a failed result; errors before payment are
        raised.

        The order is sent with a random ``checkout_id``, or the one in
        ``data`` (16 to 64 letters, digits, ``-`` or ``_``; anything else is a
        :class:`ValidationException` ``checkout_invalid_checkout_id``, raised
        before anything is sent). When no answer comes back, or another
        request is still taking payment for the cart
        (``409 cocart_payment_in_progress``), the order may have been placed:
        this raises :class:`CheckoutOutcomeUnknownException`, and
        :meth:`get_status` with its ``checkout_id`` tells how it ended.

        A total that changed since the customer reviewed it (:meth:`get`) is
        ``409 cocart_checkout_total_mismatch``: get the checkout again and
        show the new total.
        """
        checkout_id = data.get("checkout_id")
        if checkout_id is None:
            checkout_id = _new_checkout_id()
        if not isinstance(checkout_id, str) or not _CHECKOUT_ID.fullmatch(checkout_id):
            raise ValidationException(
                'checkout_id must be 16 to 64 letters, digits, "-" or "_".',
                http_code=0,
                error_code="checkout_invalid_checkout_id",
            )
        body = _with_payment_data_pairs({**data, "checkout_id": checkout_id})
        if isinstance(body.get("meta_keys"), (list, tuple)):
            body["meta_keys"] = ",".join(str(key) for key in body["meta_keys"])
        try:
            return CheckoutResult.from_response(self.process(body))
        except CoCartException as e:
            if _is_lost_response(e) or _is_payment_in_progress(e):
                raise CheckoutOutcomeUnknownException(e, checkout_id) from e
            raise

    def get_status(self, checkout_id: str) -> Dict[str, Any]:
        """How a checkout ended, when :meth:`place_order` raised
        :class:`CheckoutOutcomeUnknownException`.

        Ask from the same cart, or as the same customer. Returns
        ``checkout_id``, ``code``, ``message``, and ``order_id``,
        ``order_key``, ``order_number`` and ``order_status`` (``None`` unless
        the checkout placed an order). ``code`` is:

        - ``order_placed``: show the order.
        - ``payment_required``: the order was placed but isn't paid; pay it
          with :meth:`pay_for_order`.
        - ``in_progress``: the checkout is still running; ask again in a few seconds.
        - ``not_placed``: nothing went through; place the order again.
        """
        response = self._client.request_raw("GET", f"{ROUTE}/status", params={"checkout_id": checkout_id})
        data = _dict(response.to_dict())
        result = _dict(data.get("result"))
        order = _dict(data.get("order"))
        status = _dict(order.get("status"))
        order_id = order.get("id")
        order_number = order.get("number")
        return {
            "checkout_id": data["checkout_id"] if isinstance(data.get("checkout_id"), str) else checkout_id,
            "code": result["code"] if isinstance(result.get("code"), str) else "",
            "message": result["message"] if isinstance(result.get("message"), str) else "",
            "order_id": order_id if isinstance(order_id, int) and not isinstance(order_id, bool) else None,
            "order_key": order["key"] if isinstance(order.get("key"), str) else None,
            "order_number": None if order_number is None else str(order_number),
            "order_status": status["code"] if isinstance(status.get("code"), str) else None,
        }

    def get_config(self) -> Response:
        """The store's form settings (no cart needed): fields, countries,
        shipping, account and store settings, ``order_received_url`` for
        :meth:`confirm_return`, whether address search is available
        (``address_autocomplete.enabled``, with its ``providers``), and the
        terms text with its links (``store.terms_text``, ``terms_links``,
        ``terms_url``, ``privacy_url``)."""
        return self._client.request_raw("GET", f"{ROUTE}/config")

    def get_payment_methods(self) -> Response:
        """The payment methods for this cart: ``{"payment_methods": [...]}``,
        each with ``id``, ``title``, ``supports`` and the customer's
        ``saved_tokens``."""
        return self._client.request_raw("GET", f"{ROUTE}/payment-methods")

    def get_saved_payment_methods(self, gateway_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """A logged-in customer's saved payment methods, for every gateway or one.

        Each has ``id``, ``gateway_id``, ``label`` (e.g. "Visa ending in
        4242"), ``type``, ``expires`` (or ``None``), ``is_default`` and
        ``supports_subscriptions``. Pay with one as
        ``wc-{gateway_id}-payment-token`` in ``payment_data``, or change a
        subscription's card with its ``id`` as ``token_id``. Empty for a guest.
        """
        methods = _dict(self.get_payment_methods().to_dict()).get("payment_methods")
        cards: List[Dict[str, Any]] = []
        for method in methods if isinstance(methods, list) else []:
            if not isinstance(method, dict) or not isinstance(method.get("id"), str):
                continue
            if gateway_id is not None and method["id"] != gateway_id:
                continue
            supports = _dict(method.get("supports"))
            tokens = method.get("saved_tokens")
            for token in tokens if isinstance(tokens, list) else []:
                if not isinstance(token, dict):
                    continue
                expires = token.get("expires")
                cards.append({
                    "id": int(token.get("id") or 0),
                    "gateway_id": method["id"],
                    "label": str(token.get("label") or ""),
                    "type": str(token.get("type") or ""),
                    "expires": expires if isinstance(expires, str) and expires != "" else None,
                    "is_default": token.get("is_default") is True,
                    "supports_subscriptions": supports.get("subscriptions") is True,
                })
        return cards

    def search_addresses(
        self,
        query: str,
        country: Optional[str] = None,
        type: Optional[str] = None,  # noqa: A002 - the API's parameter name
        provider: Optional[str] = None,
    ) -> Response:
        """Address suggestions (no cart needed; at least 3 characters).

        Without a server-side address provider it's
        ``404 cocart_address_search_no_provider``: check :meth:`get_config`'s
        ``address_autocomplete.enabled`` first.
        """
        params = {"query": query, "country": country, "type": type, "provider": provider}
        return self._client.request_raw(
            "GET", f"{API}/address/search", {key: value for key, value in params.items() if value is not None}
        )

    def get_address_details(self, address_id: str, provider: str) -> Response:
        """A suggestion's full address (no cart needed)."""
        return self._client.request_raw(
            "GET", f"{API}/address/details", {"address_id": address_id, "provider": provider}
        )

    def get_order_received(
        self, order_id: int, order_key: str, params: Optional[Dict[str, Any]] = None
    ) -> Response:
        """The order, for the thank-you page.

        ``order_key`` must match the order's key; a wrong key, or someone
        else's order, is ``404 cocart_order_not_found``.

        Args:
            params: Optional ``formatted`` (amounts formatted for display) and
                ``meta_keys`` (only these keys in the order's ``meta``; a list
                is comma-joined).
        """
        query = document_query(params) or {}
        query["order_key"] = order_key
        return self._client.request_raw("GET", f"{API}/order-received/{order_id}", query)

    def pay_for_order(self, order_id: int, order_key: str, data: Dict[str, Any]) -> CheckoutResult:
        """Take payment for an unpaid (``pending`` or ``failed``) order.

        Read the result as for :meth:`place_order`: a card that needs 3D Secure
        gives ``needs_confirmation()``, then call again with the same input. A
        declined card is a failed result, not an exception. The order key is
        sent in the body, not the URL. An order that needs no payment or can't
        be paid is a ``409``, and so is another payment still running for it
        (``cocart_payment_in_progress``).
        """
        body = _with_payment_data_pairs({**data, "order_key": order_key})
        return CheckoutResult.from_response(
            self._client.request_raw("POST", f"{API}/order-received/{order_id}/pay", data=body)
        )

    def confirm_order_payment(
        self, order_id: int, order_key: str, return_params: Optional[Dict[str, str]] = None
    ) -> Response:
        """Finish a payment after an off-site step, from the parameters the
        customer came back with.

        Pass every query parameter the return URL carried, unchanged. Safe to
        call more than once. See :meth:`confirm_return` to do this straight
        from the return URL.
        """
        return self._client.request_raw(
            "POST",
            f"{API}/order-received/{order_id}/confirm",
            data={"order_key": order_key, "return_params": return_params or {}},
        )

    def confirm_return(
        self, url: str, order_id: Optional[int] = None, order_key: Optional[str] = None
    ) -> CheckoutResult:
        """Finish a payment from the URL the customer returned to.

        Reads the order ID (``order_id``) and key (``key``) from the URL and
        forwards every query parameter. ``is_pending()`` means the gateway
        hasn't confirmed yet: call again shortly. Safe to call more than once.
        """
        params = _query_params(url)
        if order_id is None:
            order_id = int(params["order_id"]) if params.get("order_id", "").isdigit() else 0
        if order_key is None:
            order_key = params.get("key", "")

        if order_id <= 0 or not order_key:
            raise CoCartException(
                "The return URL has no order ID or order key. Pass them if your route carries them elsewhere.",
                error_code="checkout_return_missing_order",
            )

        return CheckoutResult.from_response(self.confirm_order_payment(order_id, order_key, params))
