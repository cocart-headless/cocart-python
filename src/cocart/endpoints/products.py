from __future__ import annotations

from typing import Any, Dict, Optional, Union
from urllib.parse import quote

from cocart.endpoints.endpoint import Endpoint
from cocart.exceptions.cocart_exception import CoCartException
from cocart.paginator import Paginator
from cocart.response import Response
from cocart.types import ProductOrderBy, SortOrder


class Products(Endpoint):
    """Products Endpoint — handles all product-related API operations.

    Products API is publicly accessible without authentication.
    """

    _endpoint = "products"

    # --- Basic retrieval ---

    def all(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get all products."""
        return self._get("", self._stringify_params(params or {}))

    def find(self, product_id: Union[int, str], params: Optional[Dict[str, Any]] = None) -> Response:
        """Get a single product by ID or SKU.

        ``GET /products/{id}`` accepts either the numeric product/variation
        ID or the product's SKU in the same path segment.
        """
        return self._get(str(product_id), self._stringify_params(params or {}))

    def find_by_slug(self, slug: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get a single product by slug. Requires CoCart Starter."""
        self._client.requires_starter("products().find_by_slug")
        return self._get(slug, self._stringify_params(params or {}))

    # --- Search & Filter ---

    def search(self, term: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Search products."""
        merged = dict(params or {})
        merged["search"] = term
        return self.all(merged)

    def by_category(self, category_slug: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get products by category."""
        merged = dict(params or {})
        merged["category"] = category_slug
        return self.all(merged)

    def by_tag(self, tag_slug: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get products by tag."""
        merged = dict(params or {})
        merged["tag"] = tag_slug
        return self.all(merged)

    def by_brand(self, brand_slug: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get products by brand. Requires CoCart Starter."""
        self._client.requires_starter("products().by_brand")
        merged = dict(params or {})
        merged["brand"] = brand_slug
        return self.all(merged)

    def featured(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get featured products."""
        merged = dict(params or {})
        merged["featured"] = True
        return self.all(merged)

    def on_sale(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get products on sale."""
        merged = dict(params or {})
        merged["on_sale"] = True
        return self.all(merged)

    def by_price_range(
        self,
        min_price: Optional[Union[int, float]] = None,
        max_price: Optional[Union[int, float]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Get products within a price range."""
        merged = dict(params or {})
        if min_price is not None:
            merged["min_price"] = min_price
        if max_price is not None:
            merged["max_price"] = max_price
        return self.all(merged)

    def sort_by(
        self,
        field: ProductOrderBy,
        order: SortOrder = "asc",
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Get products sorted by a field.

        Args:
            field: One of the sort orders CoCart accepts: ``date``, ``id``,
                ``menu_order``, ``include``, ``title``, ``slug``, ``name``,
                ``alphabetical``, ``reverse_alpha``, ``popularity``, ``sales``,
                ``rating``, ``review_count``, ``by_stock``, ``on_sale_first``,
                ``featured_first``, ``price_asc``, ``price_desc``, and with
                CoCart Starter ``relevance`` and ``rand``. Sort by price with
                ``price_asc`` or ``price_desc``: CoCart rejects ``price``.
            order: ``asc`` or ``desc``.
        """
        merged = dict(params or {})
        merged["orderby"] = field
        merged["order"] = order
        return self.all(merged)

    def by_stock_status(self, status: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get products by stock status."""
        merged = dict(params or {})
        merged["stock_status"] = status
        return self.all(merged)

    # --- Pagination ---

    def paginate(
        self,
        page: int = 1,
        per_page: int = 10,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Get a specific page of products."""
        merged = dict(params or {})
        merged["page"] = page
        merged["per_page"] = per_page
        return self.all(merged)

    def all_paginated(self, params: Optional[Dict[str, Any]] = None) -> Paginator:
        """Iterate through all pages of products automatically.

        Example::

            for page in client.products().all_paginated({"per_page": 20}):
                print(page.to_dict())

            # Or collect all pages
            pages = client.products().all_paginated({"per_page": 50}).to_list()
        """
        base_params = dict(params or {})
        return Paginator(lambda page: self.all({**base_params, "page": page}))

    # --- Variations ---

    def variations(self, product_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product variations."""
        return self._get(f"{product_id}/variations", params)

    def variation(
        self,
        product_id: int,
        variation_id: int,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Get a specific variation. Requires CoCart Starter."""
        self._client.requires_starter("products().variation")
        return self._get(f"{product_id}/variations/{variation_id}", params)

    # --- Categories ---

    def categories(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product categories."""
        return self._get("categories", params)

    def category(self, category_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single category. Requires CoCart Starter."""
        self._client.requires_starter("products().category")
        return self._get(f"categories/{category_id}", params)

    # --- Tags ---

    def tags(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product tags."""
        return self._get("tags", params)

    def tag(self, tag_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single tag. Requires CoCart Starter."""
        self._client.requires_starter("products().tag")
        return self._get(f"tags/{tag_id}", params)

    # --- Attributes ---

    def attributes(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product attributes."""
        return self._get("attributes", params)

    def attribute(self, attribute_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single attribute."""
        return self._get(f"attributes/{attribute_id}", params)

    def attribute_terms(self, attribute_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get attribute terms."""
        return self._get(f"attributes/{attribute_id}/terms", params)

    def attribute_term(
        self,
        attribute_id: int,
        term_id: int,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Get a specific term for an attribute."""
        return self._get(f"attributes/{attribute_id}/terms/{term_id}", params)

    def attribute_by_slug(self, slug: str, params: Optional[Dict[str, str]] = None) -> Response:
        """Get an attribute by its slug. Requires CoCart Starter."""
        self._client.requires_starter("products().attribute_by_slug")
        return self._get(f"attributes/{slug}", params)

    def attribute_terms_by_slug(self, slug: str, params: Optional[Dict[str, str]] = None) -> Response:
        """Get terms for an attribute by the attribute's slug. Requires CoCart Starter."""
        self._client.requires_starter("products().attribute_terms_by_slug")
        return self._get(f"attributes/{slug}/terms", params)

    def attribute_term_by_slug(
        self,
        attr_slug: str,
        term_slug: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Get a specific term by slug for an attribute by slug. Requires CoCart Starter."""
        self._client.requires_starter("products().attribute_term_by_slug")
        return self._get(f"attributes/{attr_slug}/terms/{term_slug}", params)

    # --- Brands ---

    def brands(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product brands. Requires CoCart Starter."""
        self._client.requires_starter("products().brands")
        return self._get("brands", params)

    def brand(self, brand_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single brand. Requires CoCart Starter."""
        self._client.requires_starter("products().brand")
        return self._get(f"brands/{brand_id}", params)

    # --- Reviews ---

    def reviews(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product reviews."""
        return self._get("reviews", params)

    def product_reviews(self, product_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get reviews for a specific product."""
        merged = dict(params or {})
        merged["product"] = str(product_id)
        return self._get("reviews", merged)

    def create_review(self, data: Dict[str, Any]) -> Response:
        """Post a product review.

        Args:
            data: ``product_id``, ``review``, ``rating`` (1-5), and for a guest
                ``reviewer`` and ``reviewer_email``.
        """
        return self._post("reviews", data)

    def my_reviews(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get the current authenticated user's product reviews. Requires CoCart Starter."""
        self._client.requires_starter("products().my_reviews")
        return self._get("reviews/mine", params)

    # --- Shipping rates ---

    def shipping_rates(
        self,
        product_id: Union[int, str],
        quantity: Optional[int] = None,
        variation: Optional[Dict[str, str]] = None,
        item_data: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Shipping rates for a product before it's added to the cart (CoCart Plus).

        ``product_id`` may be a variation ID or a SKU. Sent without the cart
        key: the route prices a simulated cart and refuses one
        (``400 cocart_calculate_product_shipping_rates_cart_access_denied``).
        External and grouped products can't be priced (``400``).

        Args:
            product_id: Product ID, variation ID or SKU.
            quantity: Quantity to price.
            variation: Attributes of a variable product, e.g.
                ``{"attribute_pa_color": "blue"}``.
            item_data: Custom item data, as sent when adding the item.
        """
        query: Dict[str, str] = {}
        if quantity is not None:
            query["quantity"] = str(quantity)
        for key, value in (variation or {}).items():
            query[f"variation[{key}]"] = str(value)
        for key, value in (item_data or {}).items():
            query[f"item_data[{key}]"] = str(value)

        route = (
            f"{self._client.get_namespace()}/{self._client.API_VERSION}/products/"
            f"{quote(str(product_id), safe='')}/shipping-rates"
        )
        try:
            return self._client.request_raw("GET", route, query, None, omit_cart_key=True)
        except CoCartException as e:
            self._handle_no_route(e)

    # --- SEO ---

    def seo(self, product_id: int) -> Response:
        """Get SEO data for a product by ID."""
        return self._get(f"{product_id}/seo")

    def seo_by_slug(self, slug: str) -> Response:
        """Get SEO data for a product by slug."""
        return self._get(f"{slug}/seo")
