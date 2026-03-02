from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from cocart.endpoints.endpoint import Endpoint
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

    def add_items(self, items: List[Dict[str, Any]]) -> Response:
        """Add multiple items to the cart in a single request."""
        formatted = [
            {**item, "id": str(item["id"]), "quantity": str(item["quantity"])}
            for item in items
        ]
        return self._post("add-items", {"items": formatted})

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
        """Update multiple items in a single request.

        Accepts either shorthand ``{item_key: quantity}`` or full format.
        """
        if isinstance(items, dict):
            formatted: List[Dict[str, Any]] = [
                {"item_key": key, "quantity": str(qty)}
                for key, qty in items.items()
            ]
        else:
            formatted = [
                {**item, "quantity": str(item["quantity"])}
                for item in items
            ]
        return self._post("update", {"items": formatted})

    def remove_item(self, item_key: str) -> Response:
        """Remove an item from the cart."""
        return self._delete(f"item/{item_key}")

    def remove_items(self, item_keys: List[str]) -> Response:
        """Remove multiple items from the cart."""
        items = [{"item_key": key, "quantity": "0"} for key in item_keys]
        return self._post("update", {"items": items})

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

        Requires CoCart Basic.
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
        """Update customer details.

        Args:
            billing: Billing address fields.
            shipping: Shipping address fields.
        """
        data: Dict[str, str] = {}
        for key, value in (billing or {}).items():
            data[f"billing_{key}"] = value
        for key, value in (shipping or {}).items():
            data[f"shipping_{key}"] = value
        return self._post("update", data)

    def get_customer(self) -> Response:
        """Get customer details."""
        return self._get("", {"_fields": "customer"})

    # --- Shipping ---

    def get_shipping_methods(self) -> Response:
        """Get available shipping methods."""
        return self._get("", {"_fields": "shipping"})

    def set_shipping_method(self, method_key: str) -> Response:
        """Set shipping method for the cart."""
        return self._post("set-shipping-method", {"method_key": method_key})

    def calculate_shipping(self, address: Dict[str, str]) -> Response:
        """Calculate shipping for the cart."""
        return self._post("calculate/shipping", address)

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
        variation_id: int,
        quantity: int = 1,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Shorthand: Add a variable product to cart."""
        return self.add_item(variation_id, quantity, variation=attributes or {})
