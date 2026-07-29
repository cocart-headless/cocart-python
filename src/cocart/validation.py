from __future__ import annotations

import re

from cocart.exceptions.validation_exception import ValidationException


_NUMERIC_STRING = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")


def validate_product_id(product_id: int | str) -> None:
    """Validate a product ID, mirroring the server's own resolution rules.

    A numeric value (int, or a string containing only a number) must be a
    positive integer. A non-numeric string is treated as a potential SKU
    and passed through untouched — the server resolves a non-numeric ID before 
    falling back to a 404. This SDK can't verify a SKU exists without a 
    network request, so it only rejects input that's certain to be invalid 
    (empty, or numeric but not a positive integer).
    """
    if isinstance(product_id, str) and product_id.strip() and not _NUMERIC_STRING.match(product_id):
        return  # Non-numeric string — treat as a SKU; the server resolves it.

    try:
        num_id = int(product_id)
    except (TypeError, ValueError):
        num_id = -1

    if num_id < 1:
        raise ValidationException(
            "Product ID must be a positive integer",
            http_code=0,
            error_code="cocart_invalid_product_id",
        )


def validate_quantity(quantity: int | float) -> None:
    """Validate that a quantity is a positive number."""
    if not isinstance(quantity, (int, float)) or quantity < 1:
        raise ValidationException(
            "Quantity must be a positive number",
            http_code=0,
            error_code="cocart_invalid_quantity",
        )


def validate_email(email: str) -> None:
    """Validate that an email address has a valid basic format."""
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise ValidationException(
            "A valid email address is required",
            http_code=0,
            error_code="cocart_invalid_email",
        )
