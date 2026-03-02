# CoCart Python SDK

Official Python SDK for the [CoCart](https://cocartapi.com) REST API.

> [!IMPORTANT]
> This SDK is still in development and not yet ready for production use. Provide feedback if you experience a bug.

## TODO to complete the SDK

* [ ] Add SDK docs to documentation site
* [ ] Add support for Cart API extras
* [ ] Add Checkout API support
* [ ] Add Customers Account API support

---

## Features

* Full cart management (add, update, remove, clear items)
* Guest customer support with automatic cart key tracking
* Authenticated user support (Basic Auth & JWT)
* JWT token lifecycle (login, refresh, validate, auto-refresh)
* Session management and cart transfer on login
* Fetch products easily, search and filter results
* Sessions management (admin)
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
| [Cart](docs/cart.md) | Add/update/remove items, coupons, customer details, shipping, fees, totals |
| [Products](docs/products.md) | List/search/filter products, pagination, variations, categories, tags, attributes, reviews |
| [Sessions](docs/sessions.md) | Admin sessions API, SessionManager, storage adapters, cart transfer on login |
| [Error Handling](docs/error-handling.md) | Exception hierarchy, catching errors, HTTP status mapping, response error helpers |
| [Utilities](docs/utilities.md) | Currency and timezone utility helpers that operate on data already returned by the API |

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

## Requirements

- Python 3.9+
- `requests` library

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
    main_plugin="basic",                  # "basic" (default) or "legacy"
    etag=True,                            # ETag conditional requests (default True)
    max_retries=2,                        # Retry transient failures (429, 503)
)
```

## License

MIT
