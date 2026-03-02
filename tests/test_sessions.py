from __future__ import annotations

import pytest

from cocart import CoCart
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com", consumer_key="ck_123", consumer_secret="cs_456")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestSessions:
    def test_all(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.sessions().all()
        assert "sessions" in mock_adapter.last_request["url"]

    def test_find(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.sessions().find("sess123")
        assert "session/sess123" in mock_adapter.last_request["url"]

    def test_destroy(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.sessions().destroy("sess123")
        assert mock_adapter.last_request["method"] == "DELETE"
        assert "session/sess123" in mock_adapter.last_request["url"]

    def test_get_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.sessions().get_items("sess123")
        assert "session/sess123/items" in mock_adapter.last_request["url"]

    def test_by_session(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.sessions().by_session(42)
        assert "session/42" in mock_adapter.last_request["url"]

    def test_destroy_session(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.sessions().destroy_session(42)
        assert mock_adapter.last_request["method"] == "DELETE"
        assert "session/42" in mock_adapter.last_request["url"]
