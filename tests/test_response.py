from __future__ import annotations

import json
from pathlib import Path

from cocart.response import Response

FIXTURES = Path(__file__).parent / "fixtures"


class TestDataAccess:
    def test_to_dict(self) -> None:
        r = Response(200, {}, '{"name": "Test"}')
        assert r.to_dict() == {"name": "Test"}

    def test_to_dict_invalid_json(self) -> None:
        r = Response(200, {}, "not json")
        assert r.to_dict() == {}

    def test_to_json(self) -> None:
        r = Response(200, {}, '{"a": 1}')
        parsed = json.loads(r.to_json())
        assert parsed == {"a": 1}

    def test_to_json_compact(self) -> None:
        r = Response(200, {}, '{"a": 1}')
        assert "\n" not in r.to_json(pretty=False)

    def test_is_successful(self) -> None:
        assert Response(200, {}, "{}").is_successful()
        assert Response(201, {}, "{}").is_successful()
        assert not Response(400, {}, "{}").is_successful()
        assert not Response(500, {}, "{}").is_successful()

    def test_is_error(self) -> None:
        assert not Response(200, {}, "{}").is_error()
        assert Response(400, {}, "{}").is_error()
        assert Response(500, {}, "{}").is_error()


class TestDotNotation:
    def test_get_simple(self) -> None:
        r = Response(200, {}, '{"name": "Widget"}')
        assert r.get("name") == "Widget"

    def test_get_nested(self) -> None:
        r = Response(200, {}, '{"totals": {"subtotal": "1000"}}')
        assert r.get("totals.subtotal") == "1000"

    def test_get_array_index(self) -> None:
        r = Response(200, {}, '{"items": [{"name": "A"}, {"name": "B"}]}')
        assert r.get("items.0.name") == "A"
        assert r.get("items.1.name") == "B"

    def test_get_default(self) -> None:
        r = Response(200, {}, '{}')
        assert r.get("missing", "default") == "default"
        assert r.get("missing") is None

    def test_has(self) -> None:
        r = Response(200, {}, '{"a": {"b": 1}}')
        assert r.has("a")
        assert r.has("a.b")
        assert not r.has("a.c")
        assert not r.has("x")


class TestHeaders:
    def test_get_header_case_insensitive(self) -> None:
        r = Response(200, {"X-Custom": "val", "Content-Type": "application/json"}, "{}")
        assert r.get_header("x-custom") == "val"
        assert r.get_header("X-CUSTOM") == "val"
        assert r.get_header("content-type") == "application/json"

    def test_get_header_default(self) -> None:
        r = Response(200, {}, "{}")
        assert r.get_header("missing") is None
        assert r.get_header("missing", "fallback") == "fallback"


class TestCartHelpers:
    CART_BODY = json.dumps({
        "cart_hash": "abc123",
        "items": [{"item_key": "k1", "name": "Widget", "quantity": {"value": 2}}],
        "item_count": 2,
        "coupons": [{"coupon": "SAVE10", "saving": "500"}],
        "customer": {"billing_address": {"first_name": "John"}},
        "currency": {"currency_code": "USD", "currency_symbol": "$"},
        "shipping": [{"package_name": "Shipping", "rates": {}}],
        "fees": [{"name": "Service", "fee": "100"}],
        "cross_sells": [{"id": 5, "name": "Related"}],
        "totals": {"subtotal": "1000", "total": "1500"},
        "notices": {"success": ["Added"]},
    })

    def test_cart_key_from_header(self) -> None:
        r = Response(200, {"Cart-Key": "mykey"}, "{}")
        assert r.get_cart_key() == "mykey"

    def test_cart_hash(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_cart_hash() == "abc123"

    def test_items(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert len(r.get_items()) == 1
        assert r.get_items()[0]["name"] == "Widget"

    def test_item_count(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_item_count() == 2
        assert r.has_items()
        assert not r.is_empty()

    def test_empty_cart(self) -> None:
        r = Response(200, {}, '{"item_count": 0, "items": []}')
        assert r.get_item_count() == 0
        assert not r.has_items()
        assert r.is_empty()

    def test_coupons(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.has_coupons()
        assert r.get_coupons()[0]["coupon"] == "SAVE10"

    def test_customer(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_customer()["billing_address"]["first_name"] == "John"

    def test_currency(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_currency()["currency_code"] == "USD"

    def test_shipping(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert len(r.get_shipping_methods()) == 1

    def test_fees(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert len(r.get_fees()) == 1

    def test_cross_sells(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert len(r.get_cross_sells()) == 1

    def test_totals(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_totals()["total"] == "1500"

    def test_notices(self) -> None:
        r = Response(200, {}, self.CART_BODY)
        assert r.get_notices() == {"success": ["Added"]}


def recorded_cart() -> Response:
    """A cart recorded from CoCart Starter 5."""
    with open(FIXTURES / "cart.json", encoding="utf-8") as f:
        return Response(200, {}, f.read())


class TestCartShapes:
    """Cart shapes CoCart sends (recorded from CoCart Starter 5)."""

    def test_shipping_methods_lists_the_packages_from_shipping_packages(self) -> None:
        packages = recorded_cart().get_shipping_methods()
        assert isinstance(packages, list)
        assert len(packages) == 1
        assert packages[0]["package_name"] == "Shipment"
        assert "flat_rate:1" in packages[0]["rates"]

    def test_get_shipping_returns_the_whole_shipping_field(self) -> None:
        shipping = recorded_cart().get_shipping()
        assert shipping is not None
        assert shipping["has_calculated_shipping"] is True
        assert "default" in shipping["packages"]

    def test_shipping_methods_accepts_a_plain_list_and_is_empty_without_shipping(self) -> None:
        assert len(Response(200, {}, '{"shipping": [{"package_name": "A"}]}').get_shipping_methods()) == 1
        assert Response(200, {}, '{"items": []}').get_shipping_methods() == []
        assert Response(200, {}, '{"items": []}').get_shipping() is None

    def test_fees_lists_fees_keyed_by_fee_id(self) -> None:
        body = json.dumps({"fees": {
            "gift-wrap": {"name": "Gift wrap", "fee": "500"},
            "handling": {"name": "Handling", "fee": "150"},
        }})
        assert Response(200, {}, body).get_fees() == [
            {"name": "Gift wrap", "fee": "500"},
            {"name": "Handling", "fee": "150"},
        ]

    def test_fees_are_empty_for_empty_maps(self) -> None:
        assert Response(200, {}, '{"fees": {}}').get_fees() == []
        assert Response(200, {}, '{"fees": []}').get_fees() == []
        assert recorded_cart().get_fees() == []

    def test_notices_are_keyed_by_type(self) -> None:
        r = Response(200, {}, '{"notices": {"success": ["Item added"], "notice": ["Quantity reduced"]}}')
        assert r.get_notices() == {"success": ["Item added"], "notice": ["Quantity reduced"]}

    def test_notices_are_empty_when_there_are_none(self) -> None:
        # CoCart Starter 5 sends {}, CoCart 4.x sends [].
        assert recorded_cart().get_notices() == {}
        assert Response(200, {}, '{"notices": []}').get_notices() == {}
        assert Response(200, {}, '{"items": []}').get_notices() == {}

    def test_extensions(self) -> None:
        recurring = {"abc": {"totals": {"period": "/ month", "subtotal": "1000", "total": "1000"}}}
        r = Response(200, {}, json.dumps({"extensions": {"recurring_totals": recurring}}))
        assert r.get_extensions()["recurring_totals"] == recurring
        assert Response(200, {}, '{"extensions": []}').get_extensions() == {}
        assert Response(200, {}, '{"items": []}').get_extensions() == {}
        assert recorded_cart().get_extensions() == {}


class TestRateLimit:
    def test_reads_the_rate_limit_headers(self) -> None:
        r = Response(200, {"RateLimit-Limit": "25", "ratelimit-remaining": "24", "RateLimit-Reset": "1791108883"}, "{}")
        assert r.get_rate_limit() == {"limit": 25, "remaining": 24, "reset": 1791108883, "retry_after": None}

    def test_reads_retry_after(self) -> None:
        r = Response(429, {"RateLimit-Remaining": "0", "RateLimit-Retry-After": "30"}, "{}")
        assert r.get_rate_limit()["retry_after"] == 30
        assert r.get_rate_limit()["remaining"] == 0

    def test_is_all_none_without_the_headers(self) -> None:
        assert Response(200, {}, "{}").get_rate_limit() == {
            "limit": None, "remaining": None, "reset": None, "retry_after": None,
        }

    def test_ignores_values_that_are_not_numbers(self) -> None:
        assert Response(200, {"RateLimit-Limit": "abc", "RateLimit-Reset": ""}, "{}").get_rate_limit()["limit"] is None


class TestTaxHelpers:
    def test_get_taxes_array_shape(self) -> None:
        r = Response(200, {}, json.dumps({
            "taxes": [{"key": "US-US-1", "name": "State Tax", "price": "10.00"}],
        }))
        taxes = r.get_taxes()
        assert taxes == [{"key": "US-US-1", "name": "State Tax", "price": "10.00"}]
        assert r.has_taxes()

    def test_get_taxes_legacy_object_shape(self) -> None:
        r = Response(200, {}, json.dumps({
            "taxes": {"US-US-1": {"name": "State Tax", "price": "10.00"}},
        }))
        taxes = r.get_taxes()
        assert taxes == [{"key": "US-US-1", "name": "State Tax", "price": "10.00"}]
        assert r.has_taxes()

    def test_get_taxes_empty(self) -> None:
        r = Response(200, {}, "{}")
        assert r.get_taxes() == []
        assert not r.has_taxes()


class TestPagination:
    def test_pagination_headers(self) -> None:
        r = Response(200, {"X-WP-Total": "50", "X-WP-TotalPages": "5"}, "[]")
        assert r.get_total_results() == 50
        assert r.get_total_pages() == 5

    def test_pagination_headers_missing(self) -> None:
        r = Response(200, {}, "[]")
        assert r.get_total_results() is None
        assert r.get_total_pages() is None


class TestCacheHelpers:
    def test_etag(self) -> None:
        r = Response(200, {"ETag": '"abc"'}, "{}")
        assert r.get_etag() == '"abc"'

    def test_not_modified(self) -> None:
        assert Response(304, {}, "").is_not_modified()
        assert not Response(200, {}, "{}").is_not_modified()

    def test_cache_status(self) -> None:
        r = Response(200, {"CoCart-Cache": "HIT"}, "{}")
        assert r.get_cache_status() == "HIT"


class TestErrorHelpers:
    def test_error_code(self) -> None:
        r = Response(400, {}, '{"code": "invalid_product", "message": "Not found"}')
        assert r.get_error_code() == "invalid_product"
        assert r.get_error_message() == "Not found"

    def test_no_error(self) -> None:
        r = Response(200, {}, '{"code": "ok"}')
        assert r.get_error_code() is None
        assert r.get_error_message() is None
