from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from cocart.endpoints.endpoint import Endpoint
from cocart.paginator import Paginator
from cocart.response import Response


class Products(Endpoint):
    """Products Endpoint — handles all product-related API operations.

    Products API is publicly accessible without authentication.
    """

    _endpoint = "products"

    # --- Basic retrieval ---

    def all(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get all products."""
        return self._get("", self._stringify_params(params or {}))

    def find(self, product_id: int, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get a single product by ID."""
        return self._get(str(product_id), self._stringify_params(params or {}))

    def find_by_slug(self, slug: str, params: Optional[Dict[str, Any]] = None) -> Response:
        """Get a single product by slug. Requires CoCart Basic."""
        self._client.requires_basic("products().find_by_slug")
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
        """Get products by brand. Requires CoCart Basic."""
        self._client.requires_basic("products().by_brand")
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
        field: str,
        order: str = "asc",
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Get products sorted by a field."""
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
        """Get a specific variation. Requires CoCart Basic."""
        self._client.requires_basic("products().variation")
        return self._get(f"{product_id}/variations/{variation_id}", params)

    # --- Categories ---

    def categories(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product categories."""
        return self._get("categories", params)

    def category(self, category_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single category. Requires CoCart Basic."""
        self._client.requires_basic("products().category")
        return self._get(f"categories/{category_id}", params)

    # --- Tags ---

    def tags(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product tags."""
        return self._get("tags", params)

    def tag(self, tag_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single tag. Requires CoCart Basic."""
        self._client.requires_basic("products().tag")
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
        """Get an attribute by its slug. Requires CoCart Basic."""
        self._client.requires_basic("products().attribute_by_slug")
        return self._get(f"attributes/{slug}", params)

    def attribute_terms_by_slug(self, slug: str, params: Optional[Dict[str, str]] = None) -> Response:
        """Get terms for an attribute by the attribute's slug. Requires CoCart Basic."""
        self._client.requires_basic("products().attribute_terms_by_slug")
        return self._get(f"attributes/{slug}/terms", params)

    def attribute_term_by_slug(
        self,
        attr_slug: str,
        term_slug: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Get a specific term by slug for an attribute by slug. Requires CoCart Basic."""
        self._client.requires_basic("products().attribute_term_by_slug")
        return self._get(f"attributes/{attr_slug}/terms/{term_slug}", params)

    # --- Brands ---

    def brands(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get product brands. Requires CoCart Basic."""
        self._client.requires_basic("products().brands")
        return self._get("brands", params)

    def brand(self, brand_id: int, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a single brand. Requires CoCart Basic."""
        self._client.requires_basic("products().brand")
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

    def my_reviews(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get the current authenticated user's product reviews. Requires CoCart Basic."""
        self._client.requires_basic("products().my_reviews")
        return self._get("reviews/mine", params)

    # --- SEO ---

    def seo(self, product_id: int) -> Response:
        """Get SEO data for a product by ID."""
        return self._get(f"{product_id}/seo")

    def seo_by_slug(self, slug: str) -> Response:
        """Get SEO data for a product by slug."""
        return self._get(f"{slug}/seo")
