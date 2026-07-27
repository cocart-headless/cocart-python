# Account API

> [!IMPORTANT]
> The Account API is supported by this SDK, but not yet available in a
> released version of the CoCart plugin — it's coming soon. This
> documentation is ready for when it ships.

The Account API gives an authenticated customer access to their own profile,
order history, downloads, and reviews via the fixed `cocart/v2/my-account`
route.

* Requires the customer to be authenticated (Basic Auth or JWT) — see
  [Authentication](authentication.md).
* If the CoCart plugin providing this route isn't installed, a
  `cocart_plugin_required` error is raised.

```python
account = client.account()
```

## Profile

### Get Profile

```python
response = client.account().get_profile()
```

### Update Profile

```python
response = client.account().update_profile({
    "account_first_name": "John",
    "account_last_name": "Doe",
    "account_display_name": "John Doe",
    "account_email": "john@example.com",
})
```

### Change Password

```python
response = client.account().change_password(
    current="old-password",
    password="new-password",
    confirm="new-password",
)
```

## Orders

### Get Order History

```python
response = client.account().get_orders()

# With parameters
response = client.account().get_orders({"page": "2", "per_page": "10", "order": "DESC"})
```

### Get a Single Order

```python
response = client.account().get_order(123)
```

### Get a Guest Order

Look up a guest order by ID and the billing email used when placing it:

```python
response = client.account().get_guest_order(123, "customer@email.com")
```

## Downloads

### Get Downloads for an Order

```python
response = client.account().get_order_downloads(123)
```

### Get Downloads for a Guest Order

```python
response = client.account().get_guest_order_downloads(123, "customer@email.com")
```

### Get All Downloads

```python
response = client.account().get_downloads()
```

## Reviews

### Get the Customer's Reviews

```python
response = client.account().get_reviews()
```
