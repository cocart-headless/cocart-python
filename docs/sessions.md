# Sessions API

## Admin Sessions Endpoint

The Sessions endpoint is for administrators to manage cart sessions server-side. It requires WooCommerce REST API credentials.

```python
from cocart import CoCart

client = CoCart("https://your-store.com",
    consumer_key="ck_xxxxx",
    consumer_secret="cs_xxxxx",
)
```

### List All Sessions

```python
response = client.sessions().all()

# With parameters
response = client.sessions().all({"per_page": "50"})
```

### Find a Session

```python
# By cart key
response = client.sessions().find("guest_abc123")

# By customer ID
response = client.sessions().by_session(123)
```

### Get Session Items

```python
response = client.sessions().get_items("guest_abc123")
```

### Delete a Session

```python
# By cart key
response = client.sessions().destroy("guest_abc123")

# By customer ID
response = client.sessions().destroy_session(123)
```

---

## SessionManager

The `SessionManager` class handles cart sessions for frontend applications — tracking guest carts, persisting cart keys, and managing the guest-to-authenticated transition.

### Basic Setup

```python
from cocart import CoCart
from cocart.session_manager import SessionManager
from cocart.storage.file_storage import FileStorage

client = CoCart("https://your-store.com")
storage = FileStorage("/tmp/cocart-sessions")
session = SessionManager(client, storage)
```

### Initialize a Cart

Creates a guest cart and persists the cart key:

```python
cart_key = session.initialize_cart()
print(cart_key)  # "guest_abc123..."

# The cart key is now stored via the storage adapter
# On the next request, SessionManager restores it automatically
```

### Login with Basic Auth

```python
# Guest adds items first
client.cart().add_item(123, quantity=2)

# Login and merge guest cart into customer cart
response = session.login("customer@email.com", "password", merge_cart=True)

# Or login without merging (starts fresh customer cart)
response = session.login("customer@email.com", "password", merge_cart=False)
```

### Login with JWT

```python
# Guest adds items
client.cart().add_item(123, quantity=2)

# Login via JWT and merge cart
response = session.login_with_jwt("customer@email.com", "password", merge_cart=True)

# Access JWT manager for token operations
session.jwt().validate()
session.jwt().refresh()
```

### Login with Existing JWT Token

```python
response = session.login_with_token("eyJ...")
```

### Logout

```python
session.logout()

# Start a new guest session
session.initialize_cart()
```

### Session Status

```python
session.is_authenticated()  # True if Basic Auth or JWT is set
session.is_guest()          # True if no auth credentials
session.get_cart_key()      # Current cart key or None
```

### Custom Storage Key

```python
session.set_storage_key("my_app_cart_key")
```

---

## Storage Adapters

Storage adapters implement `StorageInterface` and are used by both `SessionManager` (for cart keys) and `JwtManager` (for JWT tokens).

### Memory Storage

Stores data in a Python dict (default, lost when process ends):

```python
from cocart.storage.memory_storage import MemoryStorage

storage = MemoryStorage()
```

### File Storage

Stores data in the filesystem:

```python
from cocart.storage.file_storage import FileStorage

storage = FileStorage("/tmp/cocart-sessions")
```

### Custom Storage

Implement `StorageInterface` for any storage backend:

```python
from cocart.storage.storage import StorageInterface


class RedisStorage:
    """Redis-backed storage adapter."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def get(self, key: str) -> str | None:
        value = self._redis.get(key)
        return value.decode() if value else None

    def set(self, key: str, value: str) -> None:
        self._redis.set(key, value)

    def delete(self, key: str) -> None:
        self._redis.delete(key)
```

Usage:

```python
import redis

r = redis.Redis(host="127.0.0.1", port=6379)

storage = RedisStorage(r)
session = SessionManager(client, storage)
jwt = JwtManager(client, storage)
```

---

## Cart Transfer on Login

A common flow for headless stores: the guest browses and adds items, then logs in and their cart transfers to their account.

```python
from cocart import CoCart
from cocart.session_manager import SessionManager
from cocart.storage.file_storage import FileStorage

client = CoCart("https://your-store.com")
storage = FileStorage("/tmp/cocart-sessions")
session = SessionManager(client, storage)

# 1. Initialize guest session
session.initialize_cart()

# 2. Guest browses and adds items
client.cart().add_item(123, quantity=2)
client.cart().add_item(456, quantity=1)

# 3. Guest decides to log in
session.login_with_jwt("customer@email.com", "password", merge_cart=True)

# 4. Guest cart items are now in the customer's cart
cart = client.cart().get()
items = cart.get_items()  # Contains items 123 and 456

# 5. Later, customer logs out
session.logout()
session.initialize_cart()  # Fresh guest session
```

See [Authentication](authentication.md) for more on JWT and Basic Auth setup.
