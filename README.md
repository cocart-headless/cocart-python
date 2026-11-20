# CoCart Python SDK

Official Python SDK for the [CoCart](https://cocartapi.com) REST API.

[![Tests](https://img.shields.io/github/actions/workflow/status/cocart-headless/cocart-python/tests.yml?label=tests&style=for-the-badge&labelColor=000000)](https://github.com/cocart-headless/cocart-python/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/cocart-headless/cocart-python?color=9cf&style=for-the-badge&labelColor=000000)](https://github.com/cocart-headless/cocart-python/blob/main/LICENSE)

> [!IMPORTANT]
> This SDK is still in development and not yet ready for production use. Provide feedback if you experience a bug.

## TODO to complete the SDK

* [ ] Add SDK docs to documentation site
* [ ] Add support for Cart API extras
* [x] Add Checkout API support — implemented ([`client.checkout()`](docs/checkout.md)); needs CoCart Plus 2.0, which isn't released yet
* [x] Add Customers Account API support — implemented ([`client.account()`](docs/account.md)); needs CoCart Plus 2.0, which isn't released yet

---

## Requirements

- Python 3.11+
- `requests` library
- CoCart plugin installed on your WooCommerce store
- CoCart Plus 2.0 for the account and checkout APIs (not released yet)
- CoCart JWT Authentication plugin (optional, for JWT auth)

## Support Policy

See [SUPPORT.md](SUPPORT.md) for our versioning policy, supported Python versions, and support lifecycle.

## Features

* Full cart management (add, update, remove, clear items)
* Batch requests — single round-trip for multiple sub-requests (CoCart Plus)
* Guest customer support with automatic cart key tracking
* Authenticated user support (Basic Auth & JWT)
* JWT token lifecycle (login, 2FA verification, refresh, validate, auto-refresh)
* Session management and cart transfer on login
* Fetch products easily, search and filter results
* Sessions management (admin)
* Customer account access (registration, profile, orders, downloads, reviews, subscriptions)
* Checkout and payment (CoCart Plus 2.0): place orders, 3D Secure, off-site steps, saved payment methods, recovering a checkout that got no answer
* Multiple storage adapters for cart key and token persistence
* Multiple HTTP adapters (`requests` default, `httpx` optional)
* `typing.Protocol` interfaces for easy mocking in tests
* ETag conditional requests for reduced bandwidth (enabled by default)
* Legacy CoCart plugin support with version-aware endpoint guards
* Comprehensive error handling with typed exceptions
* Iterator-based pagination with Python `for` loop support
* Fluent interface — all setters return `self` for chaining
* Currency formatting and timezone utilities

## Documentation

| Guide | Description |
|-------|-------------|
| [Installation](docs/installation.md) | Requirements, pip install, HTTP adapters, configuration options |
| [Authentication](docs/authentication.md) | Guest sessions, Basic Auth, JWT (login/refresh/validate/auto-refresh), consumer keys, white-labelling |
| [Cart](docs/cart.md) | Add/update/remove items, batch requests, coupons, customer details, shipping, fees, totals |
| [Products](docs/products.md) | List/search/filter products, pagination, variations, categories, tags, attributes, reviews |
| [Account](docs/account.md) | Registration, customer profile, password, address, order history, downloads, reviews and subscriptions (needs CoCart Plus 2.0, not released yet) |
| [Checkout](docs/checkout.md) | Place orders and take payment, 3D Secure, off-site steps, saved payment methods, the thank-you page, paying for unpaid orders, when no answer comes back (needs CoCart Plus 2.0, not released yet) |
| [Sessions](docs/sessions.md) | Admin sessions API, SessionManager, storage adapters, cart transfer on login |
| [Error Handling](docs/error-handling.md) | Exception hierarchy, catching errors, HTTP status mapping, response error helpers, expired carts, rate limits |
| [Utilities](docs/utilities.md) | Currency and timezone utility helpers that operate on data already returned by the API |
| [Extension Data](docs/extension-data.md) | Plugin data under `extensions` (CoCart Plus integrations), and sending a plan, gift or warranty choice |

## Installation

```bash
pip install cocart
```

## Quick Start

```python
from cocart import CoCart

# Initialize the client
client = CoCart("https://your-store.com")

# Browse products
products = client.products().all()
print(products.to_dict())

# Add item to cart
response = client.cart().add_item(42, quantity=2)
print(f"Cart key: {response.get_cart_key()}")

# Get cart
cart = client.cart().get()
print(f"Items: {cart.get_item_count()}")
print(f"Total: {cart.get_totals().get('total')}")
```

## Checkout

With CoCart Plus 2.0. The browser turns the card into a payment method ID with the gateway's own JavaScript (for Stripe, Stripe.js with a publishable key such as `pk_test_…`); your server places the order with that ID. `payment_data` carries gateway tokens only, never card numbers.

```python
from cocart import CheckoutOutcomeUnknownException

checkout = client.checkout()

# On the review page: get() snapshots the total CoCart Plus will charge.
# Don't call it just before placing the order.
review = checkout.get()

# Save what the customer enters, and show what couldn't be applied.
updated = checkout.update({"billing_address": address, "shipping_method": "flat_rate:1"})
updated.get("result.not_applied")   # [{"field", "code", "message"}]

try:
    result = checkout.place_order({
        "billing_address": address,
        "shipping_method": "flat_rate:1",
        "payment_method": "stripe",
        "payment_data": {"wc-stripe-payment-method": payment_method_id},
    })
except CheckoutOutcomeUnknownException as e:
    # No answer came back, or another request is still paying (409 cocart_payment_in_progress).
    status = checkout.get_status(e.checkout_id)
    status["code"]  # "order_placed", "payment_required" (pay_for_order()), "in_progress" (ask again) or "not_placed" (place again)
else:
    if result.is_complete():
        order = checkout.get_order_received(result.order_id, result.order_key)
    elif result.is_awaiting_payment():
        ...  # Placed: the customer pays with the gateway's SDK (a wallet, a voucher, BLIK…)
    elif result.needs_confirmation():
        ...  # 3D Secure: confirm result.client_secret in the page, then make the same call again
    elif result.needs_redirect():
        ...  # Send the customer to result.redirect_url, then call confirm_return() when they're back
    elif result.is_pending():
        ...  # Not confirmed yet: confirm again shortly
    elif result.is_failed():
        print(result.message)  # Plain text; pay again with pay_for_order()
```

A `CheckoutResult` has `code` (`order_placed`, `action_required`, `payment_pending`, `payment_failed`, or `payment_method_changed` for a subscription), `object`, `order_id`, `order_key`, `order_number`, `order_status`, `subscription_id`, `redirect_url`, `client_secret`, `intent_type`, `payment_method_type`, `message`, `error_code`, `gateway_error_code`, `gateway_message`, `action_type`, `action_data` and the raw `response`. Printing it never shows `client_secret` or `order_key`. A total that changed since the review page is `409 cocart_checkout_total_mismatch`: get the checkout again and show the new total. Saved payment methods (`get_saved_payment_methods()`) come with a `label` such as "Visa ending in 4242". See [Checkout](docs/checkout.md).

On a server, use **one client per customer** (per request, or per session): the client holds the customer's cart key or login.

## Authentication

```python
# Basic Auth
client = CoCart("https://your-store.com", username="user@email.com", password="password")

# JWT Auth
client = CoCart("https://your-store.com")
client.login("user@email.com", "password")

# WooCommerce API keys (admin)
client = CoCart("https://your-store.com", consumer_key="ck_xxx", consumer_secret="cs_xxx")
```

## Configuration

```python
client = CoCart("https://your-store.com",
    cart_key="existing_cart_key",          # Guest session
    username="customer@email.com",        # Basic Auth
    password="password",
    jwt_token="your-jwt-token",           # JWT Auth
    jwt_refresh_token="your-refresh-token",
    consumer_key="ck_xxxxx",              # Admin (Sessions API)
    consumer_secret="cs_xxxxx",
    auth_header_name="Authorization",     # Custom auth header for proxies
    timeout=30,                           # HTTP settings
    verify_ssl=True,
    rest_prefix="wp-json",               # Custom REST prefix
    namespace="cocart",                   # Custom namespace (WhiteLabel add-on)
    main_plugin="starter",                # "starter" (default) or "legacy"
    etag=True,                            # ETag conditional requests (default True)
    max_retries=2,                        # Retry 429s; 503s and timeouts for GETs only
)
```

## CoCart Channels

We have different channels at your disposal where you can find information about the CoCart project, discuss it and get involved:

[![Twitter: cocartapi](https://img.shields.io/twitter/follow/cocartapi?style=social)](https://twitter.com/cocartapi) [![CoCart GitHub Stars](https://img.shields.io/github/stars/cocart-headless/cocart-python?style=social)](https://github.com/cocart-headless/cocart-python)

<ul>
  <li>📖 <strong>Documentation</strong>: this is the place to learn how to use CoCart API. <a href="https://cocartapi.com/docs/?utm_medium=gh&utm_source=github&utm_campaign=readme&utm_content=cocart">Get started!</a></li>
  <li>👪 <strong>Community</strong>: use our Discord chat room to share any doubts, feedback and meet great people. This is your place too to share <a href="https://cocartapi.com/community/?utm_medium=gh&utm_source=github&utm_campaign=readme&utm_content=cocart">how are you planning to use CoCart!</a></li>
  <li>🐞 <strong>GitHub</strong>: we use GitHub for bugs and pull requests, doubts are solved with the community.</li>
  <li>🐦 <strong>Social media</strong>: a more informal place to interact with CoCart users, reach out to us on <a href="https://twitter.com/cocartapi">X/Twitter.</a></li>
</ul>

## Credits

Website [cocartapi.com](https://cocartapi.com/?ref=github) &nbsp;&middot;&nbsp;
GitHub [@cocart-headless](https://github.com/cocart-headless) &nbsp;&middot;&nbsp;
X/Twitter [@cocartapi](https://twitter.com/cocartapi) &nbsp;&middot;&nbsp;
[Facebook](https://www.facebook.com/cocartforwc/) &nbsp;&middot;&nbsp;
[Instagram](https://www.instagram.com/cocartheadless/)

## License

MIT
