from __future__ import annotations

import json

from cocart.response import Response


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
        "notices": [{"type": "success", "message": "Added"}],
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
        assert len(r.get_notices()) == 1


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
