# Authentication

CoCart supports multiple authentication methods depending on the use case.

## Guest Customers

No authentication is needed for guest cart operations. The SDK automatically manages the cart session for you:

1. **First request** — No cart key exists yet. The CoCart server creates a new guest session and returns a `Cart-Key` header in the response.
2. **SDK extracts it** — The SDK reads the `Cart-Key` header and stores it on the client instance automatically.
3. **Subsequent requests** — The stored cart key is sent as both a `Cart-Key` header and a `cart_key` query parameter, so the server knows which cart to use.

```python
from cocart import CoCart

client = CoCart("https://your-store.com")

# Add item — cart key is extracted from the response automatically
client.cart().add_item(123, quantity=2)

print(client.get_cart_key())  # "guest_abc123..."

# Subsequent requests use the stored cart key
cart = client.cart().get()  # Same cart as before
```

### Storage for Cart Key Persistence

By default, the SDK stores the cart key in memory. For web applications, use a storage adapter to persist between requests:

```python
from cocart import CoCart
from cocart.storage.file_storage import FileStorage

storage = FileStorage("/tmp/cocart-sessions")
client = CoCart("https://your-store.com", storage=storage)
```

### Resuming with a Known Cart Key

If you already have a cart key (e.g. stored in your own database), pass it directly:

```python
client = CoCart("https://your-store.com", cart_key="existing_cart_key")
```

## Basic Auth

For authenticated customers using WordPress username/password:

```python
client = CoCart("https://your-store.com",
    username="customer@email.com",
    password="customer_password",
)

# Or set at runtime
client = CoCart("https://your-store.com")
client.set_auth("customer@email.com", "password")

# Check auth status
client.is_authenticated()  # True
client.is_guest()          # False
```

## JWT Authentication

If the [CoCart JWT Authentication](https://wordpress.org/plugins/cocart-jwt-authentication/) plugin (v3.0+) is installed, `login()` acquires JWT tokens automatically. If the plugin is not installed, `login()` raises an `AuthenticationException`. For stores without JWT, use Basic Auth directly via `set_auth()`.

### Login

```python
client = CoCart("https://your-store.com")

# Login — acquires JWT tokens (requires CoCart JWT Authentication plugin)
response = client.login("customer@email.com", "password")

print(response.get("display_name"))  # "john"
print(response.get("user_id"))       # "123"

# Subsequent requests automatically use the acquired credentials
cart = client.cart().get()
```

### Logout

```python
client.logout()  # Calls server logout endpoint, then clears local JWT and refresh tokens
```

### Refresh an Expired Token

```python
client.jwt().refresh()
```

### Validate a Token

```python
if client.jwt().validate():
    print("Token is valid")
else:
    print("Token is expired or invalid")
```

### Check Token Expiry

Check if the token is expired locally without making an API call:

```python
# Check if expired (with 30-second leeway by default)
if client.jwt().is_token_expired():
    client.jwt().refresh()

# Custom leeway (e.g., refresh 5 minutes before expiry)
if client.jwt().is_token_expired(300):
    client.jwt().refresh()

# Get the expiry timestamp
expiry = client.jwt().get_token_expiry()
if expiry is not None:
    from datetime import datetime
    print(f"Token expires at: {datetime.fromtimestamp(expiry)}")
```

### Auto-Refresh

Expired tokens are automatically refreshed and retried. This is enabled by default when using `client.login()`. If you set a JWT token manually, you can enable it explicitly:

```python
client.set_jwt_token("eyJ...")
client.set_refresh_token("refresh_hash_...")
client.jwt().set_auto_refresh(True)

# Expired tokens are refreshed and retried automatically
cart = client.cart().get()
```

### Persisting Tokens Across Requests

Pass a storage adapter to the JWT Manager for automatic persistence:

```python
from cocart import CoCart
from cocart.jwt_manager import JwtManager
from cocart.storage.file_storage import FileStorage

storage = FileStorage("/tmp/cocart-tokens")
client = CoCart("https://your-store.com")
jwt = JwtManager(client, storage)

# Tokens are saved to storage after login/refresh
jwt.login("user@example.com", "password")

# On subsequent runs, restore tokens from storage
client2 = CoCart("https://your-store.com")
jwt2 = JwtManager(client2, storage)
jwt2.restore_tokens_from_storage()
# client2 now has the stored JWT token — no need to login again
```

### JWT Utility Methods

```python
client.jwt().has_tokens()              # True if a JWT token is set
client.jwt().is_token_expired()        # True if token is expired (local check)
client.jwt().get_token_expiry()        # Unix timestamp of token expiry
client.jwt().is_auto_refresh_enabled() # Check auto-refresh status
client.jwt().set_auto_refresh(True)    # Enable/disable at runtime
```

## Two-Factor Authentication (2FA)

If the [WordPress Two Factor plugin](https://wordpress.org/plugins/two-factor/) is installed and a user has 2FA enabled, the server returns a `401` challenge response on the first login attempt instead of tokens. CoCart Plus v1.6.0+ and CoCart Community v4.8+ are required.

The SDK surfaces this as a `TwoFactorRequiredException`, which you catch and handle before completing login with the OTP code.

### Basic Flow

```python
from cocart import CoCart
from cocart.exceptions import TwoFactorRequiredException

client = CoCart("https://your-store.com")

try:
    response = client.login("customer@email.com", "password")
    # No 2FA required — login complete
except TwoFactorRequiredException as e:
    # Prompt the user for their code, then complete login
    code = input("Enter your 2FA code: ")  # e.g. "123456"

    response = client.login_with_2fa("customer@email.com", "password", code)

print(response.get("display_name"))  # "john"
```

### Inspecting the Challenge

The exception carries metadata from the server about which 2FA providers are available:

```python
except TwoFactorRequiredException as e:
    providers  = e.available_providers  # ["email", "totp"]
    default    = e.default_provider     # "totp"
    email_sent = e.email_sent           # True if email code was auto-sent

    # Ask the user which provider to use, then:
    response = client.login_with_2fa("customer@email.com", "password", code, provider="email")
```

### Specifying a Provider

Pass the provider name as the `provider` keyword argument. If omitted, the server uses its default:

```python
# TOTP (authenticator app)
client.login_with_2fa(username, password, totp_code, provider="totp")

# Email
client.login_with_2fa(username, password, email_code, provider="email")

# Backup code
client.login_with_2fa(username, password, backup_code, provider="backup-codes")

# Let server decide (uses last-used or primary provider)
client.login_with_2fa(username, password, code)
```

### With SessionManager (Cart Merge)

If you are using `SessionManager` and want to merge a guest cart after login:

```python
from cocart.exceptions import TwoFactorRequiredException

try:
    response = session.login_with_jwt(username, password)
except TwoFactorRequiredException as e:
    response = session.login_with_jwt_2fa(username, password, code)
    # Guest cart is merged automatically
```

### Supported 2FA Providers

| Provider | Value | Notes |
|---|---|---|
| TOTP | `"totp"` | Authenticator apps (Google Authenticator, Authy). 6-digit code, 30-second window. |
| Email | `"email"` | Code sent via email. When email is the default provider, the code is sent automatically on the first login attempt (`email_sent` is `True`). |
| Backup Codes | `"backup-codes"` | Single-use static codes for account recovery. |

## Consumer Keys (Admin)

For admin-only endpoints like Sessions API, use WooCommerce REST API credentials:

```python
client = CoCart("https://your-store.com",
    consumer_key="ck_xxxxx",
    consumer_secret="cs_xxxxx",
)

sessions = client.sessions().all()
```

## Authentication Priority

When multiple auth credentials are configured, the SDK uses this priority:

1. **JWT Token** (`jwt_token`) — Bearer token
2. **Basic Auth** (`username` / `password`) — Basic auth header
3. **Consumer Keys** (`consumer_key` / `consumer_secret`) — Basic auth header

### Switching Auth at Runtime

```python
# Start with JWT
client = CoCart("https://your-store.com", jwt_token="eyJ...")

# Switch to Basic Auth (clears JWT)
client.set_auth("user", "pass")

# Switch to JWT (clears Basic Auth)
client.set_jwt_token("new.jwt.token")

# Clear everything
client.clear_session()
```

## White-Labelling / Custom REST Prefix

If your WordPress site uses a custom REST URL prefix (via `rest_url_prefix` filter) or CoCart has been white-labelled with a different namespace:

```python
# Custom REST prefix (site uses /api/ instead of /wp-json/)
client = CoCart("https://your-store.com", rest_prefix="api")
# Requests go to: https://your-store.com/api/cocart/v2/cart

# White-labelled namespace
client = CoCart("https://your-store.com", namespace="mystore")
# Requests go to: https://your-store.com/wp-json/mystore/v2/cart

# Both together
client = CoCart("https://your-store.com", rest_prefix="api", namespace="mystore")
# Requests go to: https://your-store.com/api/mystore/v2/cart

# Or set at runtime
client.set_rest_prefix("api").set_namespace("mystore")
```

JWT endpoints also respect the namespace automatically:

```python
# Refresh calls: {rest_prefix}/{namespace}/jwt/refresh-token
# Validate calls: {rest_prefix}/{namespace}/jwt/validate-token
```

## Custom Auth Header

Some hosting providers or reverse proxies (Cloudflare, Nginx, Apache) strip or block the standard `Authorization` header. You can configure the SDK to use an alternative header name:

```python
# Via constructor
client = CoCart("https://your-store.com",
    username="customer@email.com",
    password="password",
    auth_header_name="X-Authorization",
)

# Or at runtime
client.set_auth_header_name("X-Authorization")
```

The SDK will send credentials using the custom header instead:

```
X-Authorization: Basic dXNlcjpwYXNz
X-Authorization: Bearer eyJ...
```

Your WordPress server must be configured to read the custom header. For example, in `.htaccess`:

```apache
RewriteEngine On
RewriteCond %{HTTP:X-Authorization} ^(.+)$
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:X-Authorization}]
```

## Testing with Mocks

Use the SDK's `HttpAdapter` Protocol for easy mocking in tests:

```python
from cocart import CoCart
from tests.mock_http_adapter import MockHttpAdapter

mock = MockHttpAdapter()
mock.queue(200, body='{"items": [], "item_count": 0}')

client = CoCart("https://example.com")
client._http_adapter = mock

response = client.cart().get()
assert response.get_item_count() == 0
```
