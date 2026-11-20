from __future__ import annotations

from cocart.exceptions.cocart_exception import CoCartException


class CheckoutOutcomeUnknownException(CoCartException):
    """``place_order()`` sent the order but doesn't know how it ended.

    No answer came back (the connection dropped, the request timed out, or a
    proxy gave up waiting), or another request is still taking payment for the
    cart (``409 cocart_payment_in_progress``), so the order may or may not have
    been placed. Don't place it again blindly: ask
    ``checkout().get_status(e.checkout_id)`` how it ended. Keeps the original
    error's message and codes.
    """

    def __init__(self, cause: CoCartException, checkout_id: str) -> None:
        super().__init__(str(cause), cause.http_code, cause.error_code, cause.response_data)
        self.checkout_id = checkout_id
        """The ``checkout_id`` the order was sent with."""
        self.__cause__ = cause
