from __future__ import annotations

import pytest

from cocart import CoCart
from cocart.exceptions import CoCartException
from cocart.storage.memory_storage import MemoryStorage
from tests.mock_http_adapter import MockHttpAdapter

INVALID_CART = '{"code": "cocart_invalid_cart", "message": "Cart is not valid.", "data": {"status": 404}}'


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def storage() -> MemoryStorage:
    s = MemoryStorage()
    s.set("cocart_cart_key", "t_expired")
    return s


def make_client(mock_adapter: MockHttpAdapter, storage: MemoryStorage, **kwargs: str) -> CoCart:
    c = CoCart("https://example.com", storage=storage, **kwargs)
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestInvalidCartRecovery:
    """CoCart Starter 5 refuses a cart key with no cart session (e.g. an expired cart)."""

    def test_forgets_the_stored_key_and_retries_once_as_a_new_guest(
        self, mock_adapter: MockHttpAdapter, storage: MemoryStorage
    ) -> None:
        client = make_client(mock_adapter, storage)
        assert client.get_cart_key() == "t_expired"

        mock_adapter.queue(404, body=INVALID_CART)
        mock_adapter.queue(200, {"Cart-Key": "t_fresh"}, '{"items": []}')
        response = client.cart().get()

        assert response.is_successful()
        assert len(mock_adapter.requests) == 2
        assert "cart_key=t_expired" in mock_adapter.requests[0]["url"]
        assert "cart_key" not in mock_adapter.requests[1]["url"]
        assert "Cart-Key" not in mock_adapter.requests[1]["headers"]
        assert client.get_cart_key() == "t_fresh"
        assert storage.get("cocart_cart_key") == "t_fresh"

    def test_retries_a_write_too(self, mock_adapter: MockHttpAdapter, storage: MemoryStorage) -> None:
        client = make_client(mock_adapter, storage)
        mock_adapter.queue(404, body=INVALID_CART)
        mock_adapter.queue(200, {"Cart-Key": "t_fresh"}, '{"items": [{"item_key": "abc"}]}')
        client.cart().add_item(42, 1)

        assert [r["method"] for r in mock_adapter.requests] == ["POST", "POST"]
        assert mock_adapter.requests[0]["body"] == mock_adapter.requests[1]["body"]

    def test_retries_only_once(self, mock_adapter: MockHttpAdapter, storage: MemoryStorage) -> None:
        client = make_client(mock_adapter, storage)
        mock_adapter.queue(404, body=INVALID_CART)
        mock_adapter.queue(404, body=INVALID_CART)

        with pytest.raises(CoCartException) as exc_info:
            client.cart().get()

        assert exc_info.value.error_code == "cocart_invalid_cart"
        assert len(mock_adapter.requests) == 2

    def test_does_not_retry_without_a_cart_key(self, mock_adapter: MockHttpAdapter) -> None:
        client = make_client(mock_adapter, MemoryStorage())
        mock_adapter.queue(404, body=INVALID_CART)

        with pytest.raises(CoCartException):
            client.cart().get()

        assert len(mock_adapter.requests) == 1

    def test_does_not_retry_when_logged_in(self, mock_adapter: MockHttpAdapter, storage: MemoryStorage) -> None:
        client = make_client(mock_adapter, storage, username="user", password="pass")
        mock_adapter.queue(404, body=INVALID_CART)

        with pytest.raises(CoCartException):
            client.cart().get()

        assert len(mock_adapter.requests) == 1
        assert storage.get("cocart_cart_key") == "t_expired"

    def test_leaves_other_errors_alone(self, mock_adapter: MockHttpAdapter, storage: MemoryStorage) -> None:
        client = make_client(mock_adapter, storage)
        mock_adapter.queue(404, body='{"code": "cocart_item_not_in_cart", "message": "Item not in cart."}')

        with pytest.raises(CoCartException) as exc_info:
            client.cart().get_item("abc")

        assert exc_info.value.error_code == "cocart_item_not_in_cart"
        assert len(mock_adapter.requests) == 1
        assert client.get_cart_key() == "t_expired"
        assert storage.get("cocart_cart_key") == "t_expired"


class TestSessionRestore:
    """The cart key kept by the storage adapter is picked up on construction."""

    def test_restores_the_cart_key_without_restore_session(self, storage: MemoryStorage) -> None:
        assert CoCart("https://example.com", storage=storage).get_cart_key() == "t_expired"

    def test_reads_the_key_named_after_storage_key(self) -> None:
        storage = MemoryStorage()
        storage.set("shop_cart", "t_named")
        assert CoCart("https://example.com", storage=storage, storage_key="shop_cart").get_cart_key() == "t_named"

    def test_prefers_an_explicit_cart_key(self, storage: MemoryStorage) -> None:
        assert CoCart("https://example.com", storage=storage, cart_key="t_given").get_cart_key() == "t_given"

    def test_starts_without_a_cart_key_when_storage_fails(self) -> None:
        class BrokenStorage(MemoryStorage):
            def get(self, key: str) -> None:
                raise OSError("unreadable")

        assert CoCart("https://example.com", storage=BrokenStorage()).get_cart_key() is None

    def test_restores_from_file_storage(self, tmp_path: object) -> None:
        from cocart.storage.file_storage import FileStorage

        FileStorage(str(tmp_path)).set("cocart_cart_key", "t_from_file")
        assert CoCart("https://example.com", storage=FileStorage(str(tmp_path))).get_cart_key() == "t_from_file"
