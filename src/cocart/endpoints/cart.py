from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union, cast

from cocart.endpoints.endpoint import Endpoint
from cocart.exceptions.validation_exception import ValidationException
from cocart.response import Response
from cocart.validation import validate_product_id, validate_quantity


class Cart(Endpoint):
    """Cart Endpoint — handles all cart-related API operations."""

    _endpoint = "cart"

    # --- Get cart ---

    def get(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get the cart contents."""
        return self._client.get(self._endpoint, params)

    def get_filtered(self, fields: List[str]) -> Response:
        """Get specific fields from the cart.

        Example::

            response = client.cart().get_filtered(["items", "totals"])
        """
        return self._client.get(self._endpoint, {"_fields": ",".join(fields)})

    # --- Items ---

    def add_item(
        self,
        product_id: Union[str, int],
        quantity: int = 1,
        **options: Any,
    ) -> Response:
        """Add an item to the cart.

        Args:
            product_id: Product ID or variation ID.
            quantity: Quantity to add.
            **options: Additional options (variation, item_data, etc.).
        """
        validate_product_id(product_id)
        validate_quantity(quantity)
        data: Dict[str, Any] = {
            "id": str(product_id),
            "quantity": str(quantity),
            **options,
        }
        return self._post("add-item", data)

    def add_items(
        self,
        grouped_product_id: Union[str, int],
        items: Union[Dict[str, int], List[Dict[str, Any]]],
    ) -> Response:
        """Add multiple children of a WooCommerce Grouped Product to the cart
        in a single request, via the dedicated ``cart/add-items`` endpoint.

        This is NOT a generic "add several unrelated products" call — the
        server requires a single grouped product ID plus a map of that
        group's child product IDs to quantities. For adding unrelated
        products in one request, use :meth:`CoCart.batch` instead.

        Args:
            grouped_product_id: The parent grouped product's ID.
            items: Map of child product ID => quantity (shorthand), or a
                list of ``{id, quantity}`` entries.
        """
        validate_product_id(grouped_product_id)

        if isinstance(items, dict):
            entries: List[Tuple[Any, Any]] = list(items.items())
        else:
            entries = [(item["id"], item["quantity"]) for item in items]

        if not entries:
            raise ValidationException(
                "add_items() requires at least one item.",
                http_code=0,
                error_code="cocart_invalid_items",
            )

        quantity = {str(child_id): str(qty) for child_id, qty in entries}

        return self._post("add-items", {"id": str(grouped_product_id), "quantity": quantity})

    def update_item(
        self,
        item_key: str,
        quantity: int,
        **options: Any,
    ) -> Response:
        """Update an item in the cart.

        Args:
            item_key: The cart item key.
            quantity: New quantity.
            **options: Additional options.
        """
        validate_quantity(quantity)
        data: Dict[str, Any] = {"quantity": str(quantity), **options}
        return self._post(f"item/{item_key}", data)

    def update_items(
        self,
        items: Union[Dict[str, int], List[Dict[str, Any]]],
    ) -> Response:
        """Update multiple items' quantities, one request per item, sequentially.

        There is no real bulk-update endpoint (``POST /cart/update`` is a
        namespace-dispatch route, not a bulk quantity updater), so this loops
        one :meth:`update_item` request per entry and returns the response
        from the last update (reflects the fully-updated cart). For a true
        single round trip, use :meth:`batch_update_items` instead (requires
        CoCart Plus).

        Accepts either shorthand ``{item_key: quantity}`` or full format.
        """
        entries = self._normalize_item_entries(items)

        if not entries:
            raise ValidationException(
                "update_items() requires at least one item.",
                http_code=0,
                error_code="cocart_invalid_items",
            )

        response: Optional[Response] = None
        for item_key, quantity in entries:
            response = self.update_item(item_key, quantity)

        return cast(Response, response)

    def batch_update_items(
        self,
        items: Union[Dict[str, int], List[Dict[str, Any]]],
    ) -> Response:
        """Update multiple items' quantities in a single request via the
        ``batch`` endpoint (requires CoCart Plus). Unlike :meth:`update_items`,
        this is a true single round trip instead of one sequential request
        per item.

        Accepts the same shorthand/full formats as :meth:`update_items`.
        """
        entries = self._normalize_item_entries(items)

        if not entries:
            raise ValidationException(
                "batch_update_items() requires at least one item.",
                http_code=0,
                error_code="cocart_invalid_items",
            )

        requests = [
            {
                "method": "POST",
                "path": self._batch_path(f"item/{item_key}"),
                "body": {"quantity": str(quantity)},
            }
            for item_key, quantity in entries
        ]

        return self._client.batch(requests)

    def remove_item(self, item_key: str) -> Response:
        """Remove an item from the cart."""
        return self._delete(f"item/{item_key}")

    def remove_items(self, item_keys: List[str]) -> Response:
        """Remove multiple items from the cart, one request per item,
        sequentially. Returns the response from the last removal (reflects
        the fully-updated cart). For a true single round trip, use
        :meth:`batch_remove_items` instead (requires CoCart Plus).
        """
        if not item_keys:
            raise ValidationException(
                "remove_items() requires at least one item key.",
                http_code=0,
                error_code="cocart_invalid_items",
            )

        response: Optional[Response] = None
        for item_key in item_keys:
            response = self.remove_item(item_key)

        return cast(Response, response)

    def batch_remove_items(self, item_keys: List[str]) -> Response:
        """Remove multiple items in a single request via the ``batch``
        endpoint (requires CoCart Plus). Unlike :meth:`remove_items`, this is
        a true single round trip instead of one sequential request per item.
        """
        if not item_keys:
            raise ValidationException(
                "batch_remove_items() requires at least one item key.",
                http_code=0,
                error_code="cocart_invalid_items",
            )

        requests = [
            {"method": "DELETE", "path": self._batch_path(f"item/{item_key}")}
            for item_key in item_keys
        ]

        return self._client.batch(requests)

    def restore_item(self, item_key: str) -> Response:
        """Restore a removed item to the cart."""
        return self._put(f"item/{item_key}")

    def get_removed_items(self) -> Response:
        """Get removed items that can be restored."""
        return self._get("", {"_fields": "removed_items"})

    # --- Bulk ---

    def clear(self) -> Response:
        """Clear all items from the cart."""
        return self._post("clear")

    def empty(self) -> Response:
        """Alias for :meth:`clear`."""
        return self.clear()

    def calculate(self, params: Optional[Dict[str, Any]] = None) -> Response:
        """Calculate cart totals."""
        return self._post("calculate", params)

    def get_totals(self, html: bool = False) -> Response:
        """Get cart totals."""
        params = {"html": "true"} if html else None
        return self._client.get("cart/totals", params)

    def get_item_count(self) -> Response:
        """Get count of items in cart."""
        return self._client.get("cart/items/count")

    def create(self) -> Response:
        """Create a new guest cart session without adding items.

        Requires CoCart Starter.
        """
        self._client.requires_basic("cart().create")
        return self._post("")

    def get_items(self, params: Optional[Dict[str, str]] = None) -> Response:
        """Get all items in the cart."""
        return self._get("items", params)

    def get_item(self, item_key: str, params: Optional[Dict[str, str]] = None) -> Response:
        """Get a specific item from the cart by item key."""
        return self._get(f"item/{item_key}", params)

    def update(self, data: Dict[str, Any]) -> Response:
        """Update the entire cart."""
        return self._post("update", data)

    # --- Coupons ---

    def apply_coupon(self, coupon_code: str) -> Response:
        """Apply a coupon to the cart."""
        return self._post("apply-coupon", {"coupon": coupon_code})

    def remove_coupon(self, coupon_code: str) -> Response:
        """Remove a coupon from the cart."""
        return self._delete(f"coupons/{coupon_code}")

    def get_coupons(self) -> Response:
        """Get applied coupons."""
        return self._get("", {"_fields": "coupons"})

    def check_coupons(self) -> Response:
        """Check if applied coupons are still valid."""
        return self._get("coupons/validate")

    # --- Customer ---

    def update_customer(
        self,
        billing: Optional[Dict[str, str]] = None,
        shipping: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Update customer billing (and optionally shipping) address on the cart.

        Posts to the ``update-customer`` callback on ``POST /cart/update`` —
        billing fields are sent unprefixed (``first_name``, ``address_1``,
        ...) and shipping fields are sent ``s_``-prefixed (``s_first_name``,
        ``s_address_1``, ...), which the server always validates as required
        for any address field the destination country marks required,
        independent of whether ``ship_to_different_address`` is set. If
        ``shipping`` is omitted or empty, billing is mirrored into the ``s_``
        fields so that check passes and the shipping address matches billing,
        same as leaving "ship to a different address" unchecked at a normal
        WooCommerce checkout.

        Args:
            billing: Billing address fields (unprefixed, e.g. ``first_name``,
                ``address_1``, ``city``, ``postcode``, ``country``, ``email``,
                ``phone``).
            shipping: Shipping address fields, if different from billing.
                Omit to mirror billing.
        """
        billing = billing or {}
        shipping = shipping or {}
        ship_to = shipping if shipping else billing

        data: Dict[str, Any] = {"namespace": "update-customer"}
        for key, value in billing.items():
            data[key] = value
        for key, value in ship_to.items():
            data[f"s_{key}"] = value
        if shipping:
            data["ship_to_different_address"] = True

        return self._post("update", data)

    def get_customer(self) -> Response:
        """Get customer details."""
        return self._get("", {"_fields": "customer"})

    # --- Shipping ---

    def get_shipping_methods(self) -> Response:
        """Get available shipping methods."""
        return self._get("", {"_fields": "shipping"})

    def set_shipping_method(self, rate_id: str, package_id: Optional[str] = None) -> Response:
        """Select a shipping rate for a package (CoCart Plus).

        Posts ``rate_id`` (and optional ``package_id``) to
        ``POST /cart/set-shipping-method``. Omit ``package_id`` to apply the
        rate to every package.

        Args:
            rate_id: The chosen rate's key, e.g. ``flat_rate:2`` (see a
                shipping package's ``rates`` map).
            package_id: Restrict the selection to one package. Omit to apply
                to all packages.
        """
        data: Dict[str, Any] = {"rate_id": rate_id}
        if package_id:
            data["package_id"] = package_id
        return self._post("set-shipping-method", data)

    def calculate_shipping(self, address: Optional[Dict[str, str]] = None) -> Response:
        """@deprecated There is no address-taking shipping-calculation
        endpoint in the CoCart REST API — ``POST /cart/calculate/shipping``
        (what this method used to call) does not exist. To calculate
        shipping, call :meth:`update_customer` with the destination address
        first (the server recalculates totals as part of that request); this
        method now just delegates to :meth:`calculate`, ignoring ``address``.
        Prefer :meth:`calculate` directly.
        """
        return self.calculate()

    # --- Fees ---

    def get_fees(self) -> Response:
        """Get cart fees."""
        return self._get("", {"_fields": "fees"})

    def add_fee(self, name: str, amount: float, taxable: bool = False) -> Response:
        """Add a fee to the cart."""
        return self._post("add-fee", {"name": name, "amount": amount, "taxable": taxable})

    def remove_fees(self) -> Response:
        """Remove all fees from the cart."""
        return self._post("remove-fees")

    # --- Cross-sells ---

    def get_cross_sells(self) -> Response:
        """Get cross-sell product recommendations."""
        return self._get("", {"_fields": "cross_sells"})

    # --- Shorthands ---

    def add(self, product_id: int, quantity: int = 1) -> Response:
        """Shorthand: Add a simple product to cart."""
        return self.add_item(product_id, quantity)

    def add_variation(
        self,
        variation_id: Union[int, str],
        quantity: int = 1,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Shorthand: Add a variable product to cart. `variation_id` accepts a SKU too."""
        return self.add_item(variation_id, quantity, variation=attributes or {})

    # --- Internal ---

    @staticmethod
    def _normalize_item_entries(
        items: Union[Dict[str, int], List[Dict[str, Any]]],
    ) -> List[Tuple[str, int]]:
        """Convert the shorthand (``item_key`` => quantity) or full list
        format into ``(item_key, quantity)`` entry tuples.
        """
        if isinstance(items, dict):
            return [(str(key), qty) for key, qty in items.items()]
        return [(str(item["item_key"]), item["quantity"]) for item in items]

    def _batch_path(self, path: str) -> str:
        """Build the full versioned path for a batch sub-request, e.g.
        ``cart/item/abc123`` -> ``/cocart/v2/cart/item/abc123``.
        """
        namespace = self._client.get_namespace()
        api_version = self._client.API_VERSION
        return f"/{namespace}/{api_version}/{self._build_path(path).lstrip('/')}"
