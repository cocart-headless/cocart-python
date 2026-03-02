from __future__ import annotations

from typing import Any, Dict


class CurrencyFormatter:
    """Utility for formatting currency values using CoCart currency metadata."""

    def format(self, amount: int, currency_info: Dict[str, Any]) -> str:
        """Format a smallest-unit integer into a currency string.

        Args:
            amount: Amount in smallest currency unit (e.g. cents).
            currency_info: Currency metadata from the API.

        Returns:
            Formatted currency string (e.g. "$12.99").
        """
        minor_unit = currency_info.get("currency_minor_unit", 2)
        value = amount / (10 ** minor_unit)
        decimal_sep = currency_info.get("currency_decimal_separator", ".")
        thousand_sep = currency_info.get("currency_thousand_separator", ",")
        prefix = currency_info.get("currency_prefix", "")
        suffix = currency_info.get("currency_suffix", "")

        formatted = self._format_number(value, minor_unit, decimal_sep, thousand_sep)
        return f"{prefix}{formatted}{suffix}"

    def format_decimal(self, amount: int, currency_info: Dict[str, Any]) -> str:
        """Format a smallest-unit integer into a plain decimal string.

        Args:
            amount: Amount in smallest currency unit.
            currency_info: Currency metadata from the API.

        Returns:
            Decimal string (e.g. "12.99").
        """
        minor_unit = currency_info.get("currency_minor_unit", 2)
        value = amount / (10 ** minor_unit)
        return f"{value:.{minor_unit}f}"

    def _format_number(
        self,
        value: float,
        decimals: int,
        decimal_sep: str,
        thousand_sep: str,
    ) -> str:
        parts = f"{abs(value):.{decimals}f}".split(".")
        integer_part = parts[0]

        if thousand_sep:
            digits = list(integer_part)
            result = []
            for i, d in enumerate(reversed(digits)):
                if i > 0 and i % 3 == 0:
                    result.append(thousand_sep)
                result.append(d)
            integer_part = "".join(reversed(result))

        sign = "-" if value < 0 else ""

        if decimals > 0:
            return f"{sign}{integer_part}{decimal_sep}{parts[1]}"
        return f"{sign}{integer_part}"
