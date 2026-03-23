from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from cocart.cocart import CoCart
    from cocart.response import Response


class SessionManager:
    """Session Manager — helper for managing cart sessions.

    Useful for tracking guest customer carts and handling the transition
    to authenticated users.
    """

    def __init__(self, client: CoCart, storage: Any = None) -> None:
        self._client = client
        self._storage = storage
        self._storage_key = "cocart_cart_key"
        self._jwt_manager_instance: Any = None

    def set_storage_key(self, key: str) -> SessionManager:
        self._storage_key = key
        return self

    def get_cart_key(self) -> Optional[str]:
        return self._client.get_cart_key()

    def set_cart_key(self, cart_key: str) -> SessionManager:
        self._client.set_cart_key(cart_key)
        if self._storage:
            self._storage.set(self._storage_key, cart_key)
        return self

    def initialize_cart(self) -> Optional[str]:
        """Initialize a new cart session.

        Makes a request to the cart endpoint to get a new cart key.
        """
        response = self._client.cart().get()
        cart_key = response.get_cart_key() or self._client.get_cart_key()

        if cart_key and self._storage:
            self._storage.set(self._storage_key, cart_key)

        return cart_key

    def login(self, username: str, password: str, merge_cart: bool = True) -> Response:
        """Login with Basic Auth and optionally transfer guest cart."""
        guest_cart_key = self._client.get_cart_key()

        self._client.set_auth(username, password)
        self._clear_stored_cart_key()

        if merge_cart and guest_cart_key:
            result: Response = self._client.cart().get(params={"cart_key": guest_cart_key})
            return result

        result2: Response = self._client.cart().get()
        return result2

    def login_with_token(self, token: str) -> Response:
        """Login with an existing JWT token."""
        guest_cart_key = self._client.get_cart_key()

        self._client.set_jwt_token(token)
        self._clear_stored_cart_key()

        if guest_cart_key:
            result: Response = self._client.cart().get(params={"cart_key": guest_cart_key})
            return result

        result2: Response = self._client.cart().get()
        return result2

    def jwt(self, **kwargs: Any) -> Any:
        """Get the JWT manager instance."""
        if self._jwt_manager_instance is None:
            from cocart.jwt_manager import JwtManager

            self._jwt_manager_instance = JwtManager(self._client, self._storage, **kwargs)
        return self._jwt_manager_instance

    def login_with_jwt(self, username: str, password: str, merge_cart: bool = True) -> Response:
        """Login with JWT authentication."""
        guest_cart_key = self._client.get_cart_key()

        login_response: Response = self.jwt().login(username, password)
        self._clear_stored_cart_key()

        if merge_cart and guest_cart_key:
            self._client.cart().get(params={"cart_key": guest_cart_key})

        return login_response

    def login_with_jwt_2fa(
        self,
        username: str,
        password: str,
        code: str,
        provider: Optional[str] = None,
        merge_cart: bool = True,
    ) -> Response:
        """Complete JWT login after a TwoFactorRequiredException.

        Call this after catching TwoFactorRequiredException from login_with_jwt().
        """
        guest_cart_key = self._client.get_cart_key()

        login_response: Response = self.jwt().login_with_2fa(username, password, code, provider)
        self._clear_stored_cart_key()

        if merge_cart and guest_cart_key:
            self._client.cart().get(params={"cart_key": guest_cart_key})

        return login_response

    def logout(self) -> SessionManager:
        """Logout and start a new guest session."""
        if self._jwt_manager_instance:
            self._jwt_manager_instance.clear_tokens()
        self._client.clear_session()
        self._clear_stored_cart_key()
        return self

    def is_authenticated(self) -> bool:
        return self._client.is_authenticated()

    def is_guest(self) -> bool:
        return self._client.is_guest()

    def get_client(self) -> CoCart:
        return self._client

    def _clear_stored_cart_key(self) -> None:
        if self._storage:
            self._storage.delete(self._storage_key)
