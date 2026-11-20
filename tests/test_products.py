from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from cocart import CoCart
from cocart.exceptions import VersionException
from tests.mock_http_adapter import MockHttpAdapter


@pytest.fixture
def mock_adapter() -> MockHttpAdapter:
    return MockHttpAdapter()


@pytest.fixture
def client(mock_adapter: MockHttpAdapter) -> CoCart:
    c = CoCart("https://example.com")
    c._http_adapter = mock_adapter  # type: ignore[assignment]
    return c


class TestProductsRetrieval:
    def test_all(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().all()
        assert "products" in mock_adapter.last_request["url"]
        assert mock_adapter.last_request["method"] == "GET"

    def test_find(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"id": 42}')
        client.products().find(42)
        assert "products/42" in mock_adapter.last_request["url"]

    def test_find_accepts_sku(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{"sku": "PCT-2024"}')
        client.products().find("PCT-2024")
        assert "products/PCT-2024" in mock_adapter.last_request["url"]

    def test_find_by_slug_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.products().find_by_slug("my-product")


class TestProductsSearch:
    def test_search(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().search("widget")
        assert "search=widget" in mock_adapter.last_request["url"]

    def test_by_category(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().by_category("clothing")
        assert "category=clothing" in mock_adapter.last_request["url"]

    def test_by_tag(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().by_tag("sale")
        assert "tag=sale" in mock_adapter.last_request["url"]

    def test_featured(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().featured()
        assert "featured=True" in mock_adapter.last_request["url"]

    def test_on_sale(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().on_sale()
        assert "on_sale=True" in mock_adapter.last_request["url"]

    def test_by_price_range(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().by_price_range(10, 50)
        url = mock_adapter.last_request["url"]
        assert "min_price=10" in url
        assert "max_price=50" in url

    def test_sort_by(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        # CoCart rejects `price`: sort by price with price_asc or price_desc.
        client.products().sort_by("price_desc", "desc")
        url = mock_adapter.last_request["url"]
        assert "orderby=price_desc" in url
        assert "order=desc" in url

    def test_by_stock_status(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().by_stock_status("instock")
        assert "stock_status=instock" in mock_adapter.last_request["url"]


class TestProductsPagination:
    def test_paginate(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().paginate(2, 20)
        url = mock_adapter.last_request["url"]
        assert "page=2" in url
        assert "per_page=20" in url

    def test_all_paginated(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, headers={"x-wp-total": "2", "x-wp-totalpages": "1"}, body="[]")
        pages = client.products().all_paginated().to_list()
        assert len(pages) == 1

    def test_all_paginated_multiple_pages(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, headers={"x-wp-total": "20", "x-wp-totalpages": "2"}, body="[1,2,3]")
        mock_adapter.queue(200, headers={"x-wp-total": "20", "x-wp-totalpages": "2"}, body="[4,5]")
        pages = client.products().all_paginated().to_list()
        assert len(pages) == 2


class TestProductsVariations:
    def test_variations(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().variations(42)
        assert "42/variations" in mock_adapter.last_request["url"]

    def test_variation_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.products().variation(42, 1)


class TestProductsTaxonomies:
    def test_categories(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().categories()
        assert "categories" in mock_adapter.last_request["url"]

    def test_tags(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().tags()
        assert "tags" in mock_adapter.last_request["url"]

    def test_attributes(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().attributes()
        assert "attributes" in mock_adapter.last_request["url"]

    def test_attribute_terms(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().attribute_terms(3)
        assert "attributes/3/terms" in mock_adapter.last_request["url"]


class TestProductsBrands:
    def test_brands_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.products().brands()

    def test_by_brand_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.products().by_brand("nike")


class TestProductsReviews:
    def test_reviews(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().reviews()
        assert "reviews" in mock_adapter.last_request["url"]

    def test_product_reviews(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body="[]")
        client.products().product_reviews(42)
        assert "product=42" in mock_adapter.last_request["url"]

    def test_my_reviews_requires_starter(self) -> None:
        c = CoCart("https://example.com", main_plugin="legacy")
        with pytest.raises(VersionException):
            c.products().my_reviews()

    def test_create_review(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        data = {"product_id": 42, "review": "Great", "rating": 5, "reviewer": "Jane", "reviewer_email": "j@x.com"}
        client.products().create_review(data)
        assert mock_adapter.last_request["method"] == "POST"
        assert urlsplit(mock_adapter.last_request["url"]).path == "/wp-json/cocart/v2/products/reviews"
        assert json.loads(mock_adapter.last_request["body"]) == data


class TestProductsShippingRates:
    def test_sent_without_the_cart_key(self, mock_adapter: MockHttpAdapter) -> None:
        # The route prices a simulated cart and refuses a cart key (403).
        c = CoCart("https://example.com", cart_key="t_guest_key")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        c.products().shipping_rates(154, quantity=2)

        request = mock_adapter.last_request
        assert request["method"] == "GET"
        assert urlsplit(request["url"]).path == "/wp-json/cocart/v2/products/154/shipping-rates"
        assert parse_qs(urlsplit(request["url"]).query) == {"quantity": ["2"]}
        assert "Cart-Key" not in request["headers"]

        # Other requests keep the cart key.
        c.products().find(154)
        assert "cart_key=t_guest_key" in mock_adapter.last_request["url"]
        assert mock_adapter.last_request["headers"]["Cart-Key"] == "t_guest_key"

    def test_variation_item_data_and_sku(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        client.products().shipping_rates(
            "HOODIE/BLUE",
            variation={"attribute_pa_color": "blue"},
            item_data={"engraving": "Hi"},
        )
        url = mock_adapter.last_request["url"]
        assert urlsplit(url).path == "/wp-json/cocart/v2/products/HOODIE%2FBLUE/shipping-rates"
        assert parse_qs(urlsplit(url).query) == {
            "variation[attribute_pa_color]": ["blue"],
            "item_data[engraving]": ["Hi"],
        }

    def test_custom_namespace(self, mock_adapter: MockHttpAdapter) -> None:
        c = CoCart("https://example.com", namespace="mystore")
        c._http_adapter = mock_adapter  # type: ignore[assignment]
        c.products().shipping_rates(154)
        assert mock_adapter.last_request["url"] == "https://example.com/wp-json/mystore/v2/products/154/shipping-rates"


class TestProductsSEO:
    def test_seo(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.products().seo(42)
        assert "42/seo" in mock_adapter.last_request["url"]

    def test_seo_by_slug(self, client: CoCart, mock_adapter: MockHttpAdapter) -> None:
        mock_adapter.queue(200, body='{}')
        client.products().seo_by_slug("my-product")
        assert "my-product/seo" in mock_adapter.last_request["url"]
