# Account API

> [!IMPORTANT]
> The Account API is supported by this SDK, but not yet available in a
> released version of the CoCart plugin — it's coming soon. This
> documentation is ready for when it ships.

The Account API gives an authenticated customer access to their own profile,
password, address, order history, downloads, reviews and subscriptions via the
fixed `cocart/v2/my-account` route, plus methods that don't need a login:
registering a new customer and requesting an order withdrawal.

* All other methods require the customer to be authenticated (Basic Auth or
  JWT) — see [Authentication](authentication.md).
* If the CoCart plugin providing this route isn't installed, a
  `cocart_plugin_required` error is raised.

```python
account = client.account()
```

Each response is a document: a `customer`, an `order`, a `subscription`…, as
its `object` says. An order or subscription has `allowed_actions`, the names
of what the customer may do with it now (`pay`, `cancel`…). A change
also says what it did in `result` (`{"code", "message"}`): `account_updated`,
`account_created`, `order_cancelled`, `subscription_suspended`…

On a server, use one client per customer (per request, or per session): the
client holds the customer's login, so sharing one would share their account.

The methods that read a document take optional `formatted` (amounts formatted
for display instead of minor units) and `meta_keys` (only these keys in
`meta`; a list is comma-joined) parameters: `get_profile()`, `get_orders()`,
`get_order()`, `get_guest_order()`, `get_subscriptions()` and
`get_subscription()`.

## Register

Registers a new customer account. Unlike the other account methods,
`register()` doesn't need the customer to be logged in: it's the entry point
before authentication.

```python
client = CoCart("https://your-store.com")

response = client.account().register(
    "jane@example.com",
    "jane",               # optional if the store generates usernames from email
    "a-strong-password",  # optional if the store generates passwords
)

response.status_code         # 201
response.get("result.code")   # "account_created"
response.get("id")            # 42
response.get("username")      # "jane"
```

Registration returns `201` with the customer, as `get_profile()` gives it. It
doesn't log the customer in: log in next (see
[Authentication](authentication.md)).

The username and password are sent as `requested_username` and
`requested_password`, not `username` and `password`: CoCart treats a request
with non-empty `username`/`password` fields as a Basic Auth attempt, which
would reject the registration.

| Status | Code | Meaning |
|--------|------|---------|
| `400` | `cocart_invalid_email` | Email missing or invalid |
| `400` | `cocart_registration_invalid_username`, `cocart_registration_reserved_username` | The requested username isn't allowed (e.g. `admin`, `root`) |
| `400` | `cocart_registration_missing_password`, `cocart_registration_weak_password` | The store needs a (stronger) password |
| `400` | `cocart_account_creation_failed` | The account couldn't be created |
| `409` | `cocart_account_exists` | Email is already registered |
| `409` | `cocart_registration_username_exists` | Username is already taken |

## Profile

### Get Profile

```python
response = client.account().get_profile()

response.get("email")
response.get("billing")
response.get("recent_orders")  # the 5 most recent orders, newest first: id, number, status, date_created, total, href

# Amounts formatted for display, and only some meta keys:
response = client.account().get_profile({"formatted": True, "meta_keys": ["loyalty_tier"]})
```

### Update Profile

```python
response = client.account().update_profile({
    "account_first_name": "John",
    "account_last_name": "Doe",
    "account_display_name": "John Doe",
    "account_email": "john@example.com",
})

response.get("result.code")  # "account_updated"
```

Send only what changes. Every field at fault is reported at once
(`e.get_fields()`, see [Error Handling](error-handling.md#fields-at-fault)).

### Change Password

```python
response = client.account().change_password(
    current="old-password",
    password="new-password",
    confirm="new-password",
)
```

This sends only `password_current`, `password_1` and `password_2` to
`POST /my-account`, in one request. It returns the customer with
`account_updated` in `result`. A wrong current password is a
`ValidationException` (`cocart_account_incorrect_current_password`).

### Update Address

Saves the customer's billing and/or shipping address. Fields are unprefixed:

```python
address = {"first_name": "Jane", "address_1": "1 Main St", "city": "Paris", "postcode": "75001", "country": "FR"}
response = client.account().update_address({
    "billing_address": address,
    "shipping_address": address,
})
```

## Orders

### Get Order History

```python
response = client.account().get_orders()

response.get("orders")
response.get("pagination")
response.get_header("X-WP-Total")       # also in the headers
response.get_header("X-WP-TotalPages")

# With parameters
response = client.account().get_orders({
    "page": 2,
    "per_page": 10,
    "order": "desc",
    "status": ["processing", "on-hold"],   # one status, or a list (sent comma-joined)
    "after": "2026-01-01T00:00:00",        # ISO 8601
    "before": "2026-12-31T23:59:59",
    "subscription_order_type": "renewal",  # parent, renewal, switch or resubscribe
    "formatted": True,
    "meta_keys": ["gift_message"],
})
```

### Get a Single Order

```python
response = client.account().get_order(123)
response = client.account().get_order(123, {"formatted": True})
```

Someone else's order is `404 cocart_order_not_found`.

### Get a Guest Order

Look up a guest order by ID and the billing email used when placing it:

```python
response = client.account().get_guest_order(123, "customer@email.com")
```

A guest's order comes without its `key`. Lookups are rate limited
(`429 cocart_guest_lookup_rate_limited`).

### Cancel an Order

Cancels one of the customer's orders where WooCommerce allows it (for example
a pending or failed order):

```python
response = client.account().cancel_order(123)
response.get("result.code")   # "order_cancelled"
response.get("status.code")   # "cancelled"
```

An order that can't be cancelled is `409 cocart_order_cannot_be_cancelled`.

## Downloads

### Get Downloads for an Order

`GET /my-account/orders/{id}/downloads`, with the billing email for a guest
order. The response is the list of downloads, like `get_downloads()`.

```python
response = client.account().get_order_downloads(123)

# For a guest order
response = client.account().get_guest_order_downloads(123, "customer@email.com")

for download in response.to_dict():
    print(download["name"], download["downloads_remaining"], download["href"])  # downloads_remaining is None when unlimited
```

### Get All Downloads

```python
response = client.account().get_downloads()
response.to_dict()  # the list of downloads, in the same shape
```

## Reviews

### Get the Customer's Reviews

Returns the reviews the customer has submitted (`GET /products/reviews/mine`,
the same as `products().my_reviews()`):

```python
response = client.account().get_reviews()
```

## Email Verification

```python
# Confirm a pending email change, with the key and user ID from the emailed link.
client.account().verify_email(key, user_id)

# Prove ownership of the account email so WooCommerce links past guest orders to it (WooCommerce 11+).
sent = client.account().send_order_email_verification()
sent.get("result.code")   # "verification_sent", or "verification_throttled"
sent.get("retry_after")   # seconds before another can be asked for
client.account().verify_order_email(key, user_id)
```

## Subscriptions

Needs WooCommerce Subscriptions.

```python
subscriptions = client.account().get_subscriptions({"page": 1, "per_page": 10, "status": ["active", "on-hold"]})
subscription = client.account().get_subscription(512)
subscription = client.account().get_subscription(512, params={"formatted": True})
guest_view = client.account().get_subscription(512, "customer@email.com")

client.account().suspend_subscription(512)
client.account().reactivate_subscription(512)
client.account().cancel_subscription(512)
client.account().set_subscription_auto_renew(512, False)

# Resubscribe puts the ended subscription's items in the cart; check out as usual, or undo it.
client.account().resubscribe(512)
client.account().cancel_resubscribe(512)
```

## Changing a Subscription's Payment Method

> Requires WooCommerce Subscriptions. The customer must be logged in.

A subscription can switch to a card the customer has saved, or to a new one. Use a gateway that can charge renewals (`supports.subscriptions` in `get_payment_methods()`, `supports_subscriptions` on a saved method).

`update_subscription_payment_method()` can take payment like checkout, so it returns the same [`CheckoutResult`](checkout.md#reading-the-result). A new card may need 3D Secure.

**With a saved card:**

```python
saved = [m for m in client.checkout().get_saved_payment_methods() if m["supports_subscriptions"]]
card = saved[0]  # card["label"]: "Visa ending in 4242"

result = client.account().update_subscription_payment_method(512, {
    "payment_method": card["gateway_id"],
    "token_id": card["id"],
})
```

**With a new card**, create a payment method in the browser as in the [Quick Start](checkout.md#quick-start), with Elements in `mode: 'setup'` (nothing is charged now):

```python
result = client.account().update_subscription_payment_method(512, {
    "payment_method": "stripe",
    "payment_data": {"wc-stripe-payment-method": request.form["payment_method_id"]},
})
```

The new card is saved to the customer's account, since the renewals charge it.

**Reading the result:**

```python
if result.is_complete():
    result.code                           # "payment_method_changed"
    result.object                         # "subscription"
    result.subscription_id                # 512
    result.message                        # "Your subscription will now be paid with Visa ending in 4242."
    result.response.get("payment.title")  # "Visa ending in 4242"
elif result.needs_confirmation():
    ...  # Confirm in the browser, then call update_subscription_payment_method() again with the same input.
elif result.needs_redirect():
    return redirect(result.redirect_url)
elif result.is_pending():
    ...  # The gateway hasn't confirmed yet: check get_subscription(512) shortly.
else:
    print(result.message)
```

Confirm as in [3D Secure in the Page](checkout.md#3d-secure-in-the-page); a new card usually gives a SetupIntent (`result.intent_type` is `"setup_intent"`), which `stripe.handleNextAction()` handles too. After an off-site step, `get_subscription(512)` shows the new method.

| Code | HTTP | Meaning |
|---|---|---|
| `cocart_subscription_not_found` | 404 | No such subscription for this customer |
| `cocart_invalid_payment_method` | 400 | The gateway can't be used, or the saved card isn't the customer's |
| `cocart_subscription_payment_method_change_unsupported` | 400 | The gateway can't take over the renewals |
| `cocart_subscription_payment_token_required` | 400 | Pass a saved card's `token_id`, or a new card in `payment_data` |
| `cocart_subscription_payment_token_needs_confirmation` | 400 | The saved card must be confirmed before it can pay renewals |
| `cocart_subscription_cannot_change_payment_method` | 409 | The subscription's payment method can't be changed now |
| `cocart_payment_in_progress` | 409 | Another change is still running for this subscription |

A declined card isn't an error: it comes back as a failed result, as at checkout.

## Order Withdrawal

Submits a right-of-withdrawal request (WooCommerce's order withdrawal
feature). No login needed; the response is the same whether or not the order
matched:

```python
client.account().request_order_withdrawal({
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "email_confirmation": "jane@example.com",
    "order_number": "1042",
    "withdrawal_type": "full_order",  # or "specific_items_only" with additional_details
})
```
