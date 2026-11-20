"""Retries never send a change twice: after a timeout or a 503, a POST may
already have run on the store, so only a GET is sent again."""

from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from cocart import CoCart
from cocart.exceptions import CoCartException
from cocart.http.http_response import HttpResponse


class QueueAdapter:
    """Answers each request from a queue: a status code, or None for a timeout."""

    def __init__(self, answers: List[Optional[int]]) -> None:
        self.answers = answers
        self.calls = 0

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> HttpResponse:
        self.calls += 1
        answer = self.answers.pop(0)
        if answer is None:
            raise CoCartException("Connection timed out", http_code=0, error_code="network_error")
        body_text = '{"code": "error", "message": "Error"}' if answer >= 400 else '{"order_id": 217}'
        return HttpResponse(answer, {}, body_text)


def client(adapter: QueueAdapter, monkeypatch: pytest.MonkeyPatch) -> CoCart:
    monkeypatch.setattr("cocart.cocart.time.sleep", lambda _delay: None)
    cocart = CoCart("https://store.com", max_retries=2)
    cocart._http_adapter = adapter  # type: ignore[assignment]
    return cocart


def test_a_get_that_times_out_is_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = QueueAdapter([None, 200])
    client(adapter, monkeypatch).get("cart")
    assert adapter.calls == 2


def test_a_post_that_times_out_is_not_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = QueueAdapter([None, 200])
    with pytest.raises(CoCartException, match="timed out"):
        client(adapter, monkeypatch).post("checkout", {"payment_method": "stripe"})
    assert adapter.calls == 1


def test_a_post_answered_503_is_not_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = QueueAdapter([503, 200])
    with pytest.raises(CoCartException):
        client(adapter, monkeypatch).post("checkout", {"payment_method": "stripe"})
    assert adapter.calls == 1


def test_a_post_answered_429_is_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = QueueAdapter([429, 200])
    response = client(adapter, monkeypatch).post("checkout", {"payment_method": "stripe"})
    assert adapter.calls == 2
    assert response.get("order_id") == 217


def test_a_get_answered_503_is_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = QueueAdapter([503, 200])
    client(adapter, monkeypatch).get("cart")
    assert adapter.calls == 2
