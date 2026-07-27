# Installation

## Requirements

* Python 3.9 or higher
* One of the following HTTP clients:
  * **requests** (recommended): Installed automatically with the SDK
  * **httpx** (optional): `pip install httpx`
* CoCart plugin installed on your WooCommerce store
* [CoCart JWT Authentication](https://wordpress.org/plugins/cocart-jwt-authentication/) plugin for JWT features (optional)

## Via pip (Recommended)

```bash
pip install cocart
```

### Development Install

```bash
git clone https://github.com/cocart-headless/cocart-python.git
cd cocart-python
pip install -e ".[dev]"
```

## HTTP Adapters

The SDK uses `requests` by default. You can switch to `httpx` if installed.

| Priority | Adapter | Package | Notes |
|----------|---------|---------|-------|
| 1 | **requests** | `requests` | Default, most widely used |
| 2 | **httpx** | `httpx` | Optional, modern alternative |

### Specifying an Adapter

```python
from cocart import CoCart
from cocart.http.httpx_adapter import HttpxAdapter

# Auto-detect (uses requests by default)
client = CoCart("https://your-store.com")

# Inject a custom adapter instance
client = CoCart("https://your-store.com")
client._http_adapter = HttpxAdapter()
```

## Configuration Options

```python
client = CoCart("https://your-store.com",
    # Guest session
    cart_key="existing_cart_key",

    # Basic Auth
    username="customer@email.com",
    password="password",

    # JWT Auth
    jwt_token="your-jwt-token",
    jwt_refresh_token="your-refresh-token",

    # Admin (Sessions API)
    consumer_key="ck_xxxxx",
    consumer_secret="cs_xxxxx",

    # HTTP settings
    timeout=30,
    verify_ssl=True,

    # Custom auth header (for reverse proxies that strip Authorization)
    auth_header_name="Authorization",

    # REST API prefix (default: "wp-json")
    rest_prefix="wp-json",

    # API namespace (default: "cocart")
    namespace="cocart",

    # CoCart main plugin: "basic" (default) or "legacy"
    main_plugin="basic",

    # Retry transient failures (429, 503, timeouts)
    max_retries=2,

    # ETag conditional requests (default: True)
    etag=True,

    # Storage adapter for cart key persistence
    storage=None,           # defaults to MemoryStorage
    storage_key="cocart_cart_key",
)
```

### Fluent Configuration

```python
client = (
    CoCart.create("https://your-store.com")
    .set_timeout(60)
    .set_verify_ssl(False)
    .set_max_retries(2)
    .set_rest_prefix("api")
    .set_namespace("mystore")
    .set_auth_header_name("X-Authorization")
    .set_etag(True)
    .set_main_plugin("legacy")
    .add_header("X-Custom-Header", "value")
)
```

## Legacy Plugin Support

The SDK supports both **CoCart Starter** and the **CoCart Community plugin** (`cart-rest-api-for-woocommerce` v4.x). By default, the SDK targets CoCart Starter.

To use the SDK with the legacy plugin, set `main_plugin` to `"legacy"`:

```python
client = CoCart("https://your-store.com", main_plugin="legacy")

# Or use the fluent setter
client.set_main_plugin("legacy")
```

### What changes in legacy mode

**Basic-only methods raise immediately.** Methods that require CoCart Starter raise a `VersionException` before making any HTTP request:

```python
from cocart.exceptions import VersionException

client = CoCart("https://your-store.com", main_plugin="legacy")

try:
    client.products().find_by_slug("blue-hoodie")
except VersionException as e:
    # "products().find_by_slug() requires CoCart Starter. Please upgrade..."
    print(e)
```

Basic-only methods include:

* `cart().create()`
* `products().find_by_slug()`, `variation()`, `category()`, `tag()`
* `products().attribute_by_slug()`, `attribute_terms_by_slug()`, `attribute_term_by_slug()`
* `products().brands()`, `brand()`, `by_brand()`
* `products().my_reviews()`

**Field filtering uses `fields` instead of `_fields`.** The legacy plugin uses CoCart's custom `fields` query parameter, while CoCart Starter uses the WordPress standard `_fields`. The SDK handles this automatically.
