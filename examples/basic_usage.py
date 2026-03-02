"""CoCart Python SDK — Basic Usage Examples."""

from cocart import CoCart

# --- Guest cart (no authentication) ---

client = CoCart("https://your-store.com")

# Get store info
# store_info = client.store().info()
# print(store_info.to_dict())

# Browse products
# products = client.products().all()
# print(f"Total products: {products.get_total_results()}")

# Search products
# results = client.products().search("hoodie")

# Filter products
# featured = client.products().featured()
# on_sale = client.products().on_sale()
# by_category = client.products().by_category("clothing")
# by_price = client.products().by_price_range(10, 50)

# Paginate products
# for page in client.products().all_paginated({"per_page": 20}):
#     for product in page.to_dict():
#         print(product["name"])

# Add item to cart
# response = client.cart().add_item(42, quantity=2)
# print(f"Cart key: {response.get_cart_key()}")
# print(f"Items: {response.get_item_count()}")

# Get cart
# cart = client.cart().get()
# print(f"Total: {cart.get_totals().get('total')}")

# Update item quantity
# client.cart().update_item("item_key_here", 5)

# Apply coupon
# client.cart().apply_coupon("SAVE10")

# --- Authenticated user ---

# Basic Auth
# client = CoCart("https://your-store.com", username="user@email.com", password="password")

# JWT Auth
# client = CoCart("https://your-store.com")
# client.login("user@email.com", "password")
# cart = client.cart().get()

# --- Admin (WooCommerce API keys) ---

# admin = CoCart(
#     "https://your-store.com",
#     consumer_key="ck_xxx",
#     consumer_secret="cs_xxx",
# )
# sessions = admin.sessions().all()

# --- Response helpers ---

# response = client.cart().get()
# response.to_dict()               # Full response as dict
# response.to_json()               # Pretty JSON string
# response.get("totals.subtotal")  # Dot-notation access
# response.has("items")            # Check key exists
# response.get_items()             # Cart items list
# response.get_totals()            # Cart totals dict
# response.get_item_count()        # Item count
# response.has_items()             # Has items?
# response.is_empty()              # Is empty?
# response.get_coupons()           # Applied coupons
# response.get_customer()          # Customer details
# response.get_currency()          # Currency info
# response.get_shipping_methods()  # Shipping options
# response.is_successful()         # 2xx?
# response.is_error()              # 4xx/5xx?
