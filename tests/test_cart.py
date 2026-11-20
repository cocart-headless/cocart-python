from __future__ import annotations

import json
from urllib.parse import urlsplit

import pytest

from cocart import CoCart
from cocart.exceptions import ValidationException, VersionException
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestCartGet:
    def test_get_cart(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"items": [], "item_count": 0}')
        response = client.cart().get()
        assert response.is_successful()
        assert "cart" in mock_adapter.last_request["url"]

    def test_get_filtered(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"items": [], "totals": {}}')
        client.cart().get_filtered(["items", "totals"])
        assert "_fields=items%2Ctotals" in mock_adapter.last_request["url"]


class TestCartItems:
    def test_add_item(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"item_key": "abc"}')
        client.cart().add_item(42, 2)
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "42"
        assert body["quantity"] == "2"
        assert "add-item" in mock_adapter.last_request["url"]

    def test_add_item_validates_product_id(self, client: CoCart) -> None:
        with pytest.raises(ValidationException, match="Product ID"):
            client.cart().add_item(-1)

    def test_add_item_accepts_sku(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"item_key": "abc"}')
        client.cart().add_item("BLUE-SHIRT-L", 1)
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "BLUE-SHIRT-L"

    def test_add_item_validates_quantity(self, client: CoCart) -> None:
        with pytest.raises(ValidationException, match="Quantity"):
            client.cart().add_item(1, 0)

    def test_add_item_with_options(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_item(10, 1, variation={"size": "L"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["variation"] == {"size": "L"}

    def test_add_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_items(100, {"1": 2, "2": 1})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "100"
        assert body["quantity"] == {"1": "2", "2": "1"}
        assert "add-items" in mock_adapter.last_request["url"]

    def test_add_items_list_format(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_items(100, [{"id": 1, "quantity": 2}, {"id": 2, "quantity": 1}])
        body = json.loads(mock_adapter.last_request["body"])
        assert body["quantity"] == {"1": "2", "2": "1"}

    def test_add_items_requires_at_least_one(self, client: CoCart) -> None:
        with pytest.raises(ValidationException, match="at least one item"):
            client.cart().add_items(100, {})

    def test_update_item(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().update_item("itemkey", 5)
        body = json.loads(mock_adapter.last_request["body"])
        assert body["quantity"] == "5"
        assert "item/itemkey" in mock_adapter.last_request["url"]

    def test_update_items_shorthand(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"item_key": "k1"}')
        mock_adapter.queue(200, body='{"item_key": "k2"}')
        response = client.cart().update_items({"k1": 2, "k2": 3})
        assert len(mock_adapter.requests) == 2
        assert "item/k1" in mock_adapter.requests[0]["url"]
        assert "item/k2" in mock_adapter.requests[1]["url"]
        assert response.get("item_key") == "k2"

    def test_update_items_requires_at_least_one(self, client: CoCart) -> None:
        with pytest.raises(ValidationException, match="at least one item"):
            client.cart().update_items({})

    def test_batch_update_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().batch_update_items({"k1": 2, "k2": 3})
        body = json.loads(mock_adapter.last_request["body"])
        assert "batch" in mock_adapter.last_request["url"]
        assert len(body["requests"]) == 2
        assert body["requests"][0]["method"] == "POST"
        assert body["requests"][0]["path"] == "/cocart/v2/cart/item/k1"
        assert body["requests"][0]["body"] == {"quantity": "2"}

    def test_remove_item(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().remove_item("itemkey")
        assert mock_adapter.last_request["method"] == "DELETE"
        assert "item/itemkey" in mock_adapter.last_request["url"]

    def test_remove_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        mock_adapter.queue(200, body='{}')
        client.cart().remove_items(["k1", "k2"])
        assert len(mock_adapter.requests) == 2
        assert mock_adapter.requests[0]["method"] == "DELETE"
        assert "item/k1" in mock_adapter.requests[0]["url"]
        assert "item/k2" in mock_adapter.requests[1]["url"]

    def test_batch_remove_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().batch_remove_items(["k1", "k2"])
        body = json.loads(mock_adapter.last_request["body"])
        assert "batch" in mock_adapter.last_request["url"]
        assert len(body["requests"]) == 2
        assert body["requests"][0]["method"] == "DELETE"
        assert body["requests"][0]["path"] == "/cocart/v2/cart/item/k1"

    def test_restore_item(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().restore_item("itemkey")
        assert mock_adapter.last_request["method"] == "PUT"

    def test_get_removed_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"removed_items": []}')
        client.cart().get_removed_items()
        assert "_fields=removed_items" in mock_adapter.last_request["url"]


class TestCartBulk:
    def test_clear(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().clear()
        assert "clear" in mock_adapter.last_request["url"]

    def test_empty_alias(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().empty()
        assert "clear" in mock_adapter.last_request["url"]

    def test_calculate(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().calculate()
        assert "calculate" in mock_adapter.last_request["url"]

    def test_get_totals(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().get_totals()
        assert "cart/totals" in mock_adapter.last_request["url"]

    def test_get_totals_html(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().get_totals(html=True)
        assert "html=true" in mock_adapter.last_request["url"]

    def test_get_item_count(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().get_item_count()
        assert "items/count" in mock_adapter.last_request["url"]

    def test_create_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.cart().create()


class TestCartCoupons:
    def test_apply_coupon_sends_code(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        # CoCart Plus requires `code`; `coupon` is rejected as a missing parameter.
        mock_adapter.queue(200, body='{}')
        client.cart().apply_coupon("SAVE10")
        assert mock_adapter.last_request["method"] == "POST"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/apply-coupon"
        assert json.loads(mock_adapter.last_request["body"]) == {"code": "SAVE10"}

    def test_apply_coupon_with_email(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().apply_coupon("VIP", "jane@example.com")
        assert json.loads(mock_adapter.last_request["body"]) == {"code": "VIP", "email": "jane@example.com"}

    def test_remove_coupon(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().remove_coupon("SAVE10")
        assert mock_adapter.last_request["method"] == "DELETE"
        assert "coupons/SAVE10" in mock_adapter.last_request["url"]

    def test_remove_coupon_encodes_the_code(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        for code in ["summer sale", "10%off", "a#b?c", "café"]:
            client.cart().remove_coupon(code)
        assert [urlsplit(r["url"]).path for r in mock_adapter.requests] == [
            "/wp-json/cocart/v2/cart/coupons/summer%20sale",
            "/wp-json/cocart/v2/cart/coupons/10%25off",
            "/wp-json/cocart/v2/cart/coupons/a%23b%3Fc",
            "/wp-json/cocart/v2/cart/coupons/caf%C3%A9",
        ]
        assert all(r["method"] == "DELETE" for r in mock_adapter.requests)

    def test_remove_coupons(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().remove_coupons()
        assert mock_adapter.last_request["method"] == "DELETE"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/coupons"

    def test_check_coupons(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().check_coupons()
        assert mock_adapter.last_request["method"] == "GET"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/coupons/validate"
        assert "email" not in mock_adapter.last_request["url"]

    def test_check_coupons_with_email(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().check_coupons("jane@example.com")
        assert "email=jane%40example.com" in mock_adapter.last_request["url"]


class TestCartPlusRoutes:
    def test_get_mini(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().get_mini({"_fields": "items"})
        assert mock_adapter.last_request["method"] == "GET"
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/cart/mini"
        assert "_fields=items" in url

    def test_remove_all_items(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().remove_all_items()
        assert mock_adapter.last_request["method"] == "DELETE"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/items"

    def test_add_item_sends_plugin_choices(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().add_item(306, 1, convert_to_sub="1_month")
        client.cart().add_item(302, 1, recipient_email="friend@example.com")
        client.cart().add_item(154, 1, item_data={"warranty": "1-year"})
        bodies = [json.loads(r["body"]) for r in mock_adapter.requests]
        assert bodies[0]["convert_to_sub"] == "1_month"
        assert bodies[1]["recipient_email"] == "friend@example.com"
        assert bodies[2]["item_data"] == {"warranty": "1-year"}

    def test_change_plan(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().change_plan("abc123", "1_month")
        assert mock_adapter.last_request["method"] == "POST"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/update"
        assert json.loads(mock_adapter.last_request["body"]) == {
            "namespace": "update-item-schema",
            "item_key": "abc123",
            "convert_to_sub": "1_month",
        }

    def test_change_plan_to_one_time(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().change_plan("abc123", "0")
        assert json.loads(mock_adapter.last_request["body"])["convert_to_sub"] == "0"

    def test_change_plan_requires_an_item_key(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        with pytest.raises(ValidationException, match="item key"):
            client.cart().change_plan("", "0")
        assert mock_adapter.requests == []


class TestCartCustomer:
    def test_update_customer(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().update_customer(
            billing={"first_name": "John", "email": "john@example.com"},
            shipping={"city": "NYC"},
        )
        body = json.loads(mock_adapter.last_request["body"])
        assert body["namespace"] == "update-customer"
        assert body["first_name"] == "John"
        assert body["email"] == "john@example.com"
        assert body["s_city"] == "NYC"
        assert body["ship_to_different_address"] is True
        assert "billing_first_name" not in body
        assert "shipping_city" not in body

    def test_update_customer_mirrors_billing_when_no_shipping(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().update_customer(billing={"first_name": "John", "city": "NYC"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["namespace"] == "update-customer"
        assert body["first_name"] == "John"
        assert body["s_first_name"] == "John"
        assert body["s_city"] == "NYC"
        assert "ship_to_different_address" not in body


class TestCartShipping:
    def test_set_shipping_method(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().set_shipping_method("flat_rate:1")
        body = json.loads(mock_adapter.last_request["body"])
        assert body["rate_id"] == "flat_rate:1"
        assert "package_id" not in body

    def test_set_shipping_method_with_package_id(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().set_shipping_method("flat_rate:1", "0")
        body = json.loads(mock_adapter.last_request["body"])
        assert body["rate_id"] == "flat_rate:1"
        assert body["package_id"] == "0"

    def test_calculate_shipping_delegates_to_calculate(
        self, client: CoCart, mock_adapter: MockHttpAdapter
    ) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().calculate_shipping({"country": "US"})
        assert "calculate" in mock_adapter.last_request["url"]
        assert "shipping" not in mock_adapter.last_request["url"]


class TestCartFees:
    def test_add_fee(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_fee("Rush", 5.99, taxable=True)
        body = json.loads(mock_adapter.last_request["body"])
        assert body["name"] == "Rush"
        # CoCart Plus takes the amount as a string; a number is rejected.
        assert body["amount"] == "5.99"
        assert body["taxable"] is True
        assert "tax_class" not in body
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/cart/add-fee"

    def test_add_fee_with_tax_class(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.cart().add_fee("Gift wrap", 2.5, True, "reduced-rate")
        assert json.loads(mock_adapter.last_request["body"]) == {
            "name": "Gift wrap",
            "amount": "2.5",
            "taxable": True,
            "tax_class": "reduced-rate",
        }


class TestShorthands:
    def test_add(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add(42, 3)
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "42"
        assert body["quantity"] == "3"

    def test_add_variation(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_variation(99, 1, {"color": "red"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "99"
        assert body["variation"] == {"color": "red"}

    def test_add_variation_accepts_sku(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.cart().add_variation("VAR-SKU-1", 1, {"color": "red"})
        body = json.loads(mock_adapter.last_request["body"])
        assert body["id"] == "VAR-SKU-1"
