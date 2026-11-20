from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from cocart.response import Response

PaymentData = Union[Dict[str, Any], List[Dict[str, Any]]]


def to_payment_data_pairs(data: PaymentData) -> List[Dict[str, Any]]:
    """Turn a ``payment_data`` map into the ``{key, value}`` pairs the API takes.

    A list passes through as it is.
    """
    if isinstance(data, list):
        return data
    return [{"key": key, "value": value} for key, value in data.items()]


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value != "" else None


_WEB_URL = re.compile(r"^https?://[^\s/?#]", re.IGNORECASE)


def _web_url(value: Any) -> Optional[str]:
    """A web address the customer can be sent to: https or http only. Anything else
    (``javascript:``, ``data:``, another app's link, a relative path) is left out, so a
    response can't make a page run script or open another app."""
    url = _text(value)
    return url if url is not None and _WEB_URL.match(url) else None


def _integer(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _dict(value: Any) -> Optional[Dict[str, Any]]:
    return value if isinstance(value, dict) else None


class CheckoutResult:
    """The outcome of a call that takes payment (CoCart Plus 2.0).

    Placing an order, paying for an unpaid order, returning from an off-site
    step, or changing a subscription's payment method. Read from the
    response's ``result``. A declined card is a result (:meth:`is_failed`),
    not an exception; exceptions are kept for requests the store refuses
    before it tries to take payment.

    Attributes:
        code: ``result.code``: ``order_placed`` (paid, nothing to pay, or held
            for review or offline payment), ``action_required``,
            ``payment_pending``, ``payment_failed``, or
            ``payment_method_changed`` for a subscription. Open-ended, so a
            value a store or gateway adds comes through as it is.
        object: The document returned: ``order``, or ``subscription`` after a
            subscription's payment method change.
        order_id, order_key, order_number, order_status: The order (``id``,
            ``key``, ``number``, ``status.code``), when the document is an order.
        subscription_id: The subscription's ID, when the document is a subscription.
        redirect_url: Where to send the customer: the off-site step when
            :meth:`needs_redirect`, otherwise the page to show once the payment
            is done. Only ever an https or http address.
        client_secret, intent_type: For an in-page step (3D Secure), or a
            payment the customer makes in the page: give it to the gateway's SDK.
        payment_method_type: The Stripe payment method to pay with when
            :meth:`is_awaiting_payment` (``cashapp``, ``wechat_pay``, ``boleto``,
            ``oxxo`` or ``multibanco``).
        message: A message for the customer, for every code (plain text).
        error_code: CoCart's code for why the payment failed (``card_declined``,
            ``insufficient_funds``… or ``payment_failed``).
        gateway_error_code, gateway_message: The gateway's own code and
            message, for logging.
        action_type, action_data: What the customer must do, as the gateway
            integration names it (e.g. ``stripe_confirm_payment``), and what it needs.
        response: The raw response: the order, or the subscription.
    """

    def __init__(
        self,
        code: str,
        response: Response,
        *,
        object: Optional[str] = None,  # noqa: A002 - the API's field name
        order_id: Optional[int] = None,
        order_key: Optional[str] = None,
        order_number: Optional[str] = None,
        order_status: Optional[str] = None,
        subscription_id: Optional[int] = None,
        redirect_url: Optional[str] = None,
        client_secret: Optional[str] = None,
        intent_type: Optional[str] = None,
        payment_method_type: Optional[str] = None,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        gateway_error_code: Optional[str] = None,
        gateway_message: Optional[str] = None,
        action_type: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.object = object
        self.order_id = order_id
        self.order_key = order_key
        self.order_number = order_number
        self.order_status = order_status
        self.subscription_id = subscription_id
        self.redirect_url = redirect_url
        self.client_secret = client_secret
        self.intent_type = intent_type
        self.payment_method_type = payment_method_type
        self.message = message
        self.error_code = error_code
        self.gateway_error_code = gateway_error_code
        self.gateway_message = gateway_message
        self.action_type = action_type
        self.action_data = action_data
        self.response = response

    def __repr__(self) -> str:
        # Leaves out client_secret and order_key, so printing or logging a
        # result doesn't expose them.
        return (
            f"CheckoutResult(code={self.code!r}, object={self.object!r}, order_id={self.order_id!r}, "
            f"order_number={self.order_number!r}, order_status={self.order_status!r}, "
            f"subscription_id={self.subscription_id!r}, action_type={self.action_type!r}, "
            f"error_code={self.error_code!r})"
        )

    def is_complete(self) -> bool:
        """Paid, nothing to pay, or held for review or offline payment: the
        order is placed (or the subscription's payment method changed)."""
        return self.code in ("order_placed", "payment_method_changed") and self.action_type is None

    def is_awaiting_payment(self) -> bool:
        """The order is placed but not paid yet: the customer pays outside the checkout.

        With :attr:`client_secret`, pay in the page with the gateway's SDK for
        :attr:`payment_method_type` (Cash App Pay, WeChat Pay, a Boleto, OXXO or
        Multibanco voucher); otherwise :attr:`action_type` says what to show
        (``stripe_blik_confirmation_pending``: approve in the banking app; bank
        transfer instructions…). The gateway's webhook marks the order paid,
        so don't place the order again.
        """
        return self.code == "order_placed" and self.action_type is not None

    def needs_confirmation(self) -> bool:
        """The card needs an in-page step (3D Secure): confirm
        :attr:`client_secret` with the gateway's SDK, then make the same call again."""
        return self.code == "action_required" and self.client_secret is not None

    def needs_redirect(self) -> bool:
        """The payment needs an off-site step: send the customer to
        :attr:`redirect_url`, then call ``confirm_return()`` when they come back."""
        return (
            self.code == "action_required"
            and self.client_secret is None
            and _web_url((self.action_data or {}).get("redirect")) is not None
        )

    def is_pending(self) -> bool:
        """The gateway hasn't confirmed the payment yet: confirm again shortly, or check the order."""
        return self.code == "payment_pending"

    def is_failed(self) -> bool:
        """The payment was declined or couldn't be taken: show :attr:`message`;
        the order can be paid again."""
        return self.code == "payment_failed"

    @classmethod
    def from_response(cls, response: Response) -> CheckoutResult:
        """Read the document a call that takes payment returns, with what the
        payment did in ``result``. A missing ``result.code`` reads as
        ``payment_failed``, never as complete."""
        body = response.to_dict()
        data: Dict[str, Any] = body if isinstance(body, dict) else {}
        result = _dict(data.get("result")) or {}
        action = _dict(result.get("action"))
        action_data = _dict((action or {}).get("data"))
        error = _dict(result.get("error")) or {}
        obj = _text(data.get("object"))
        is_order = obj != "subscription"
        code = _text(result.get("code")) or "payment_failed"
        status = _dict(data.get("status")) or {}
        number = data.get("number")
        order_number = _text(number) or (str(number) if _integer(number) is not None else None)
        off_site = _web_url((action_data or {}).get("redirect"))
        # With action_required, the off-site step comes first; otherwise the
        # page to show once the payment is done.
        if code == "action_required":
            redirect_url = off_site or _web_url(result.get("redirect_url"))
        else:
            redirect_url = _web_url(result.get("redirect_url")) or off_site

        return cls(
            code,
            response,
            object=obj,
            order_id=_integer(data.get("id")) if is_order else None,
            order_key=_text(data.get("key")) if is_order else None,
            order_number=order_number if is_order else None,
            order_status=_text(status.get("code")) if is_order else None,
            subscription_id=None if is_order else _integer(data.get("id")),
            redirect_url=redirect_url,
            client_secret=_text((action_data or {}).get("client_secret")),
            intent_type=_text((action_data or {}).get("intent_type")),
            payment_method_type=_text((action_data or {}).get("payment_method_type")),
            message=_text(result.get("message")),
            error_code=_text(error.get("code")),
            gateway_error_code=_text(error.get("gateway_code")),
            gateway_message=_text(error.get("gateway_message")),
            action_type=_text((action or {}).get("type")),
            action_data=action_data,
        )
