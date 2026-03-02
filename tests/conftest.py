from __future__ import annotations

import pytest

from cocart import CoCart
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c
