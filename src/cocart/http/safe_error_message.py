from __future__ import annotations

import re

# A URL or path followed by its query string or fragment.
_URL_QUERY = re.compile(r"((?:https?://|/)[^\s?#\"'<>()]*)[?#][^\s\"'<>()]*", re.IGNORECASE)


def safe_error_message(message: str) -> str:
    """Remove the query string from any URL or path in a transport error message.

    HTTP libraries put the request URL in their connection errors (``requests``
    says "Max retries exceeded with url: /wp-json/cocart/v2/cart?cart_key=…"),
    and its query string can carry the cart key or API credentials.
    """
    return _URL_QUERY.sub(r"\1", message)
