from __future__ import annotations

import pytest

from cocart.exceptions import ValidationException
from cocart.validation import validate_email, validate_product_id, validate_quantity


class TestValidateProductId:
    def test_valid_int(self) -> None:
        validate_product_id(1)
        validate_product_id(42)

    def test_valid_string(self) -> None:
        validate_product_id("1")
        validate_product_id("42")

    def test_invalid_zero(self) -> None:
        with pytest.raises(ValidationException, match="Product ID"):
            validate_product_id(0)

    def test_invalid_negative(self) -> None:
        with pytest.raises(ValidationException, match="Product ID"):
            validate_product_id(-1)

    def test_invalid_string(self) -> None:
        with pytest.raises(ValidationException, match="Product ID"):
            validate_product_id("abc")


class TestValidateQuantity:
    def test_valid(self) -> None:
        validate_quantity(1)
        validate_quantity(100)

    def test_invalid_zero(self) -> None:
        with pytest.raises(ValidationException, match="Quantity"):
            validate_quantity(0)

    def test_invalid_negative(self) -> None:
        with pytest.raises(ValidationException, match="Quantity"):
            validate_quantity(-1)


class TestValidateEmail:
    def test_valid(self) -> None:
        validate_email("user@example.com")
        validate_email("a@b.co")

    def test_invalid_empty(self) -> None:
        with pytest.raises(ValidationException, match="email"):
            validate_email("")

    def test_invalid_no_at(self) -> None:
        with pytest.raises(ValidationException, match="email"):
            validate_email("invalid")

    def test_invalid_no_domain(self) -> None:
        with pytest.raises(ValidationException, match="email"):
            validate_email("user@")
