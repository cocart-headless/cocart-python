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

## License

MIT
