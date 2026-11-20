# Error Handling

## Exception Hierarchy

```
CoCartException (base)                (409, 429, 5xx and anything else)
├── AuthenticationException      (401, 403)
│   └── TwoFactorRequiredException  (2FA code required to complete login)
├── ValidationException          (400)
├── VersionException             (CoCart Starter required)
└── CheckoutOutcomeUnknownException  (place_order() doesn't know how the checkout ended)
```

All exceptions extend `cocart.exceptions.CoCartException`, which extends Python's built-in `Exception`.

## Catching Exceptions

```python
from cocart.exceptions import (
    CoCartException,
    AuthenticationException,
    ValidationException,
)

try:
    response = client.cart().add_item(999, quantity=1)
except ValidationException as e:
    # 400 — product not found, out of stock, invalid quantity, etc.
    print(f"Validation Error: {e}")
    print(f"Error Code: {e.error_code}")    # e.g. "cocart_product_not_found"
    print(f"HTTP Code: {e.http_code}")       # 400
except AuthenticationException as e:
    # 401 or 403 — invalid credentials, expired token, forbidden
    print(f"Auth Error: {e}")
    print(f"Error Code: {e.error_code}")     # e.g. "cocart_authentication_error"
    print(f"HTTP Code: {e.http_code}")        # 401 or 403
except CoCartException as e:
    # Any other API error (404, 500, etc.)
    print(f"API Error: {e}")
    print(f"HTTP Code: {e.http_code}")
```

## Exception Attributes

All exceptions provide these attributes and methods:

| Attribute | Type | Description |
|-----------|------|-------------|
| `args[0]` / `str(e)` | `str` | Error message: the request's method and route, the API's message and its code |
| `error_code` | `str \| None` | API error code (e.g. `cocart_product_not_found`) |
| `http_code` | `int` | HTTP status code (400, 401, 403, 500, etc.) |
| `response_data` | `dict` | Full API response body for debugging |
| `get_cart()` | `dict \| None` | The cart sent with the error (see [Item No Longer in the Cart](#item-no-longer-in-the-cart)), or `None` |
| `get_fields()` | `dict` | Every field at fault, by path, with its message (see [Fields at Fault](#fields-at-fault)); `{}` when the error isn't about fields |
| `get_field()` | `str \| None` | The first field at fault (`data.field`), e.g. `billing.postcode` |
| `get_reason()` | `str \| None` | The underlying plugin's own reason (`data.reason`), when there is one |

API error messages name the request's method and route, CoCart Plus routes (`request_raw()`) included, e.g. `POST /cocart/v2/cart/add-item: Product not found. [cocart_product_not_found]`. It never includes the full URL: its query string can carry the cart key or API credentials, so an app can log or show messages safely. Connection errors (`network_error`) lose the query string too, and don't chain the HTTP library's original exception, which holds the full URL.

## Inspecting the Full API Response

Every exception carries the full API response data for debugging:

```python
try:
    client.cart().add_item(999, quantity=1)
except CoCartException as e:
    # Full response from the API
    data = e.response_data
    # e.g. {"code": "cocart_product_not_found", "message": "...", "data": {...}}
    print(data)
```

## Fields at Fault

CoCart Plus checks a whole form at once, so one error reports every field at fault (`data.fields`), by path:

```python
try:
    client.checkout().update({"billing_address": address})
except CoCartException as e:
    e.get_fields()  # {"billing.postcode": "Enter a valid postcode.", "billing.phone": "Enter a phone number."}
    e.get_field()   # "billing.postcode": the first one
    e.get_reason()  # the underlying plugin's own reason, or None
```

## Expired JWT Tokens

Check if an auth error is specifically a token expiration:

```python
try:
    client.cart().get()
except AuthenticationException as e:
    if e.http_code == 403:
        # Token expired — refresh and retry
        client.jwt().refresh()
        cart = client.cart().get()
    else:
        # Credentials are wrong, not just expired
        raise
```

Or let the SDK handle it automatically:

```python
from cocart.jwt_manager import JwtManager

jwt = JwtManager(client, auto_refresh=True)

# Expired tokens are refreshed and retried automatically
cart = client.cart().get()
```

See [Authentication](authentication.md#auto-refresh) for details.

## Version Exceptions

When using the SDK in legacy mode, methods that require CoCart Starter raise `VersionException` immediately without making an HTTP request:

```python
from cocart.exceptions import VersionException

client = CoCart("https://your-store.com", main_plugin="legacy")

try:
    client.products().find_by_slug("blue-hoodie")
except VersionException as e:
    print(e)  # "products().find_by_slug() requires CoCart Starter..."
```

## HTTP Status Code Mapping

| HTTP Status | Exception Thrown | Typical Causes |
|-------------|-----------------|----------------|
| 400 | `ValidationException` | Invalid product ID, out of stock, invalid quantity, missing required fields |
| 401 | `AuthenticationException` | Missing or invalid credentials |
| 403 | `AuthenticationException` | Expired JWT token, insufficient permissions |
| 404 | `CoCartException` | Endpoint not found, item key not found |
| 409 | `CoCartException` | A refused state: an order that can't be paid or cancelled, a payment still in progress, a checkout total that changed |
| 429 | `CoCartException` | Rate limited |
| 5xx | `CoCartException` | Server error |

A 409, 429 or 5xx is always a plain `CoCartException`, whatever its code says (`cocart_order_invalid_status` is a 409, not a validation error). For other statuses not listed, a code containing `invalid` or `missing` gives a `ValidationException`, and one containing `authenticat` an `AuthenticationException`.

## Response Error Helpers

When you have a `Response` object, you can check for errors directly:

```python
response = client.cart().get()

if response.is_error():
    print(response.get_error_code())     # API error code
    print(response.get_error_message())  # Human-readable message
    print(response.status_code)          # HTTP status code

if response.is_successful():
    data = response.to_dict()
```

## Response Helpers

The `Response` object provides convenience methods for inspecting cart state:

```python
response = client.cart().get()

# Cart state helpers
response.has_items()     # True if cart has items
response.is_empty()      # True if cart is empty
response.has_coupons()   # True if coupons are applied

# Pagination helpers (for product listings)
response.get_total_results()  # Total items across all pages
response.get_total_pages()    # Total number of pages
```

## Common Error Scenarios

### Product Not Found

```python
try:
    client.cart().add_item(999999, quantity=1)
except ValidationException as e:
    # str(e) => "POST /cocart/v2/cart/add-item: Product not found. [cocart_product_not_found]"
    # e.error_code => "cocart_product_not_found"
    pass
```

### Out of Stock

```python
try:
    client.cart().add_item(123, quantity=100)
except ValidationException as e:
    # e.error_code => "cocart_not_enough_in_stock"
    pass
```

### Expired Cart Key

CoCart Starter 5 refuses a cart key with no cart session on every cart route (`404 cocart_invalid_cart`), for example after the cart expired. The client then forgets the stored key (in its storage too) and retries the request once as a new guest, so this error doesn't reach your code for a guest; a fresh cart key comes back as usual.

If a `SessionManager` keeps the cart key in a storage the client doesn't have, save the new key there with `session.set_cart_key(client.get_cart_key())`. See [Sessions](sessions.md).

### Item No Longer in the Cart

Getting, updating or removing an item whose key isn't in the cart (for example, another tab already removed it) fails with `404 cocart_item_not_in_cart`. Since CoCart Starter 5 the error carries the cart as it is now, so you can show it without fetching the cart again.

```python
try:
    client.cart().update_item(item_key, 2)
except CoCartException as e:
    if e.error_code == "cocart_item_not_in_cart":
        cart = e.get_cart()  # the current cart, or None with CoCart 4.x
        if cart is not None:
            render(cart)
```

### Quantity Reduced to the Maximum

Adding more than the purchase limit or the stock allows isn't an error: CoCart adds the maximum and says so with a notice.

```python
response = client.cart().add_item(123, quantity=50)
notices = response.get_notices().get("notice", [])  # ['The quantity of "Beanie" was reduced to 5, the most allowed in the cart.']
```

### Rate Limits

With rate limiting on (CoCart Plus), every response carries `RateLimit-*` headers:

```python
rate_limit = response.get_rate_limit()
# {"limit": 25, "remaining": 24, "reset": 1791108883, "retry_after": None}
```

`reset` is the Unix time the window resets, and `retry_after` the seconds to wait after a 429. Exceeding the limit returns 429 `rate_limit_exceeded`, which the client retries when `max_retries` is set, waiting as long as `RateLimit-Retry-After` says (or a proxy's `Retry-After`), up to 60 seconds. `request_raw()` (the CoCart Plus routes, such as checkout) never retries.

### Two-Factor Authentication Required

```python
from cocart.exceptions import TwoFactorRequiredException

try:
    client.login("customer@email.com", "password")
except TwoFactorRequiredException as e:
    # e.available_providers => ["email", "totp"]
    # e.default_provider    => "email"
    pass
```

See [Authentication](authentication.md#two-factor-authentication-2fa) for the full 2FA login flow.

### Invalid Input (Client-Side Validation)

The SDK validates inputs before making HTTP requests:

```python
try:
    client.cart().add_item(-1, quantity=1)
except ValueError as e:
    # "Product ID must be a positive integer"
    pass

try:
    client.cart().add_item(123, quantity=0)
except ValueError as e:
    # "Quantity must be at least 1"
    pass
```
