# Cart API

The Cart API handles all shopping cart operations.

* **Guest customers** — The first request creates a new guest session. The server returns a `Cart-Key` header which the SDK extracts and stores automatically.
* **Authenticated customers** — The server identifies the cart by the WordPress user account. No cart key is needed.

```python
cart = client.cart()
```

## Create Cart

Create a new guest cart session and get a `cart_key` without adding any items:

```python
response = client.cart().create()
cart_key = response.get("cart_key")  # "guest_abc123..."
```

> **Note:** Only available for non-authenticated (guest) users. Requires CoCart Starter.

## Get Cart

```python
response = client.cart().get()

# With parameters
response = client.cart().get(params={
    "_fields": "items,totals",  # Limit returned fields
    "thumb": "true",            # Include product thumbnails
    "default": "true",          # Return default cart data
})
```

## Get Items

Get only the items in the cart (lighter than fetching the full cart):

```python
response = client.cart().get_items()
```

### Get a Single Item

```python
response = client.cart().get_item("abc123def456...")
```

## Adding Items

### Add a Simple Product

```python
# Product ID 123, quantity 2
response = client.cart().add_item(123, quantity=2)

# Shorthand
response = client.cart().add(123, 2)

# A SKU also works — the server resolves it to a product ID
response = client.cart().add_item("BLUE-SHIRT-L", quantity=1)
```

### Add with Options

```python
response = client.cart().add_item(123, quantity=1,
    item_data={
        "gift_message": "Happy Birthday!",
        "engraving": "John",
    },
    email="customer@email.com",
    return_item=True,  # Return only the added item details
)
```

With CoCart Plus, the options also carry a subscription plan (`convert_to_sub`), a gift recipient (`recipient_email`) or a warranty (`item_data={"warranty": ...}`), and `change_plan(item_key, value)` switches a cart item's plan. See [Extension Data](extension-data.md#sending-the-customers-choices).

### Add a Variable Product

```python
response = client.cart().add_variation(456, quantity=1, attributes={
    "attribute_pa_color": "blue",
    "attribute_pa_size": "large",
})

# Or using add_item with variation option
response = client.cart().add_item(456, quantity=1, variation={
    "attribute_pa_color": "blue",
    "attribute_pa_size": "large",
})
```

### Add Multiple Children of a Grouped Product at Once

`add_items()` is for adding multiple children of a single WooCommerce
Grouped Product in one request — not for adding several unrelated products.
For that, use `client.batch()` instead (requires CoCart Plus).

```python
# Shorthand: child product ID => quantity
response = client.cart().add_items(100, {
    "123": 2,
    "456": 1,
})

# Full format
response = client.cart().add_items(100, [
    {"id": "123", "quantity": 2},
    {"id": "456", "quantity": 1},
])
```

## Updating Items

Update the quantity of a cart item using its item key:

```python
# Item keys are returned in cart responses
response = client.cart().update_item("abc123def456...", 5)

# With additional options
response = client.cart().update_item("abc123def456...", 3,
    item_data={"gift_wrap": True},
)
```

### Update Multiple Items at Once

There's no real bulk-update endpoint on the server, so `update_items()` sends
one request per item, sequentially, and returns the response from the last
update (reflecting the fully-updated cart):

```python
# Shorthand: item_key => quantity
response = client.cart().update_items({
    "abc123def456...": 3,
    "def789ghi012...": 1,
})

# Full format with additional options
response = client.cart().update_items([
    {"item_key": "abc123def456...", "quantity": 3},
    {"item_key": "def789ghi012...", "quantity": 1},
])
```

For a true single round trip (requires CoCart Plus), use
`batch_update_items()` instead — it builds the same entries into a
`client.batch()` call:

```python
response = client.cart().batch_update_items({
    "abc123def456...": 3,
    "def789ghi012...": 1,
})
```

## Removing & Restoring Items

### Remove an Item

```python
response = client.cart().remove_item("abc123def456...")
```

### Remove Multiple Items at Once

Like `update_items()`, `remove_items()` sends one request per item key,
sequentially, and returns the response from the last removal:

```python
response = client.cart().remove_items([
    "abc123def456...",
    "def789ghi012...",
])
```

For a true single round trip (requires CoCart Plus), use
`batch_remove_items()` instead:

```python
response = client.cart().batch_remove_items([
    "abc123def456...",
    "def789ghi012...",
])
```

### Restore a Removed Item

```python
response = client.cart().restore_item("abc123def456...")
```

### Get Removed Items

```python
response = client.cart().get_removed_items()
```

## Cart Management

### Clear Cart

```python
response = client.cart().clear()

# Alias
response = client.cart().empty()
```

### Remove All Items, Keep the Rest

> Requires the CoCart Plus plugin.

Removes every item but keeps the cart's coupons, fees and customer details (`DELETE /cart/items`):

```python
response = client.cart().remove_all_items()
```

### Mini Cart

> Requires the CoCart Plus plugin.

A lighter cart response for a header or drawer:

```python
response = client.cart().get_mini()
```

### Calculate Totals

```python
response = client.cart().calculate()
```

### Update Cart

```python
response = client.cart().update({
    "customer_note": "Please gift wrap.",
})
```

## Totals & Counts

### Get Totals

> `get_totals()` is a separate request to its own totals endpoint, not part of a regular cart fetch. It returns the full breakdown WooCommerce calculates, including `cart_contents_total` and the taxes per tax rate (`shipping_taxes`, `cart_contents_taxes`, `fee_taxes`).

```python
# Minor-unit strings, like the cart: {"total": "125500", ...}
response = client.cart().get_totals()

# Formatted with the currency: {"total": "$1,255.00", ...}
response = client.cart().get_totals(html=True)
```

### Get Item Count

```python
response = client.cart().get_item_count()
```

## Coupons

> Requires the CoCart Plus plugin.

### Apply a Coupon

```python
response = client.cart().apply_coupon("SUMMER20")

# A coupon restricted to certain emails, before the cart knows the customer's
response = client.cart().apply_coupon("VIP10", "jane@example.com")
```

### Remove a Coupon

```python
response = client.cart().remove_coupon("SUMMER20")

# Remove every coupon
response = client.cart().remove_coupons()
```

### Get Applied Coupons

```python
response = client.cart().get_coupons()
```

### Validate Applied Coupons

```python
response = client.cart().check_coupons()

# Including email restrictions
response = client.cart().check_coupons("jane@example.com")
```

## Customer Details

### Update Customer

`update_customer()` sends billing fields unprefixed (`first_name`,
`address_1`, ...) and shipping fields `s_`-prefixed (`s_first_name`,
`s_address_1`, ...). If `shipping` is omitted or empty, billing is mirrored
into the `s_` fields automatically — same as leaving "ship to a different
address" unchecked at a normal WooCommerce checkout.

```python
# Billing only — shipping is mirrored from billing automatically
response = client.cart().update_customer(
    billing={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "address_1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postcode": "10001",
        "country": "US",
    }
)

# Billing and a distinct shipping address (sets ship_to_different_address)
response = client.cart().update_customer(
    billing={"email": "john@example.com"},
    shipping={
        "first_name": "John",
        "last_name": "Doe",
        "address_1": "456 Oak Ave",
        "city": "Los Angeles",
        "state": "CA",
        "postcode": "90001",
        "country": "US",
    },
)
```

### Get Customer Details

```python
response = client.cart().get_customer()
```

## Shipping

### Get Available Shipping Methods

```python
response = client.cart().get_shipping_methods()

# CoCart keys the packages by package ID under `shipping.packages`;
# get_shipping_methods() on the response lists them, each with its `rates`.
for package in response.get_shipping_methods():
    for rate_id, rate in package["rates"].items():
        print(f"{rate_id}: {rate['label']} ({rate['cost']})")  # cost in minor units, e.g. "500"

# The whole field: total_packages, has_calculated_shipping, packages
shipping = response.get_shipping()
```

### Set Shipping Method

Select a shipping rate for a package (requires CoCart Plus) by its `rate_id`
(found in a shipping package's `rates` map). Pass a `package_id` to restrict
the selection to one package; omit it to apply the rate to every package.

```python
response = client.cart().set_shipping_method("flat_rate:1")

# Restrict to a specific package
response = client.cart().set_shipping_method("flat_rate:1", package_id="0")
```

### Calculate Shipping (Deprecated)

There is no address-taking shipping-calculation endpoint in the CoCart REST
API. `calculate_shipping()` is deprecated — it ignores its `address` argument
and simply delegates to `calculate()`. To calculate shipping for a
destination, call `update_customer()` with that address first (the server
recalculates totals as part of that request), then `calculate()` directly:

```python
client.cart().update_customer(billing={
    "country": "US",
    "state": "CA",
    "postcode": "90001",
    "city": "Los Angeles",
})
response = client.cart().calculate()
```

## Fees

> Requires the CoCart Plus plugin.

### Get Cart Fees

```python
response = client.cart().get_fees()

# The cart keys fees by fee ID; get_fees() lists them: [{"name": "Gift wrap", "fee": "500"}]
fees = response.get_fees()
```

### Add a Fee

```python
# Non-taxable fee
response = client.cart().add_fee("Rush Processing", 9.99)

# Taxable fee
response = client.cart().add_fee("Gift Wrapping", 4.99, taxable=True)

# Taxable, with a tax class
response = client.cart().add_fee("Gift Wrapping", 4.99, taxable=True, tax_class="reduced-rate")
```

### Remove All Fees

```python
response = client.cart().remove_fees()
```

## Cross-Sells

Get cross-sell product recommendations based on cart contents:

```python
response = client.cart().get_cross_sells()
```

## Batch Requests

`client.batch()` dispatches multiple sub-requests in a single round trip via
the `{namespace}/batch` endpoint (requires CoCart Plus). It returns one
merged, up-to-date cart response with per-operation notices, instead of one
response per request. `batch_update_items()` and `batch_remove_items()` (see
above) build their requests through this method — call it directly for
anything else you want to batch, e.g. mixing an add, a coupon, and a fee in
one request:

```python
response = client.batch([
    {"method": "POST", "path": "/cocart/v2/cart/add-item", "body": {"id": "123", "quantity": "2"}},
    {"method": "POST", "path": "/cocart/v2/cart/apply-coupon", "body": {"code": "SUMMER20"}},
    {"method": "DELETE", "path": "/cocart/v2/cart/item/abc123def456..."},
])
```

The cart returned is the one from the last sub-request that succeeded, with every sub-request's notices merged. A sub-request that failed shows up as an `error` notice, so read the notices to see what didn't apply:

```python
failed = response.get_notices().get("error", [])  # e.g. ['Coupon "SUMMER2O" does not exist!']
```

If every sub-request fails, or the batch mixes in other routes, the response is WordPress's standard batch list (`responses`, one per sub-request, with its own `status`).

## Working with Responses

All cart methods return a `Response` object with cart-specific helpers:

```python
response = client.cart().get()

# Cart items
items = response.get_items()

# Cart totals
totals = response.get_totals()

# Item count
count = response.get_item_count()

# Cart key (from headers)
cart_key = response.get_cart_key()

# Cart hash
hash = response.get_cart_hash()

# Notices, keyed by type: {"success": ["..."], "error": ["..."]}, or {} when there are none
notices = response.get_notices()

# Shipping packages as a list, and fees as a list (the cart keys both by ID)
packages = response.get_shipping_methods()
fees = response.get_fees()

# Data plugins add to the cart, e.g. subscription recurring_totals (see extension-data.md)
extensions = response.get_extensions()

# Tax lines (normalized to a flat list regardless of the server's shape)
taxes = response.get_taxes()
if response.has_taxes():
    print(taxes)

# Dot-notation access
subtotal = response.get("totals.subtotal")
first_item_name = response.get("items.0.name")

# Check if key exists
if response.has("totals.discount_total"):
    print("Discount applied!")

# Full data
data = response.to_dict()
json_str = response.to_json()
```

## ETag / Conditional Requests

The SDK automatically handles ETags for reduced bandwidth and faster responses. This is enabled by default.

When a response includes an `ETag` header, the SDK stores it in memory. On subsequent GET requests to the same URL, the SDK sends the stored ETag via the `If-None-Match` header. If the data hasn't changed, the server returns a `304 Not Modified` response with an empty body instead of the full payload.

A response whose `Cache-Control` says `no-store` or `private` is never kept, so a customer's checkout, orders or account (which CoCart Plus marks that way) don't stay in memory.

```python
client = CoCart("https://your-store.com")

# First request — full response with ETag
response = client.cart().get()
etag = response.get_etag()            # e.g. 'W/"abc123"'
cache = response.get_cache_status()   # "MISS"

# Second request — SDK sends If-None-Match automatically
response = client.cart().get()

if response.is_not_modified():
    # 304 — cart hasn't changed, use your cached data
    cache = response.get_cache_status()  # "HIT"
```

### Disabling ETags

```python
# Via constructor
client = CoCart("https://your-store.com", etag=False)

# Or at runtime
client.set_etag(False)

# Clear stored ETags without disabling
client.clear_etag_cache()
```

See [Error Handling](error-handling.md) for handling API errors.
