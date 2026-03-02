from __future__ import annotations

import re

from cocart.exceptions.validation_exception import ValidationException


def validate_product_id(product_id: int | str) -> None:
    """Validate that a product ID is a positive integer."""
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
