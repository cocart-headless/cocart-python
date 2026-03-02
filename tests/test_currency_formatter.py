from __future__ import annotations

from cocart.currency_formatter import CurrencyFormatter


class TestCurrencyFormatter:
    def setup_method(self) -> None:
        self.formatter = CurrencyFormatter()
        self.usd = {
            "currency_code": "USD",
            "currency_symbol": "$",
            "currency_minor_unit": 2,
            "currency_decimal_separator": ".",
            "currency_thousand_separator": ",",
            "currency_prefix": "$",
            "currency_suffix": "",
        }
        self.eur = {
            "currency_code": "EUR",
            "currency_symbol": "\u20ac",
            "currency_minor_unit": 2,
            "currency_decimal_separator": ",",
            "currency_thousand_separator": ".",
            "currency_prefix": "",
            "currency_suffix": " \u20ac",
        }

    def test_format_usd(self) -> None:
        assert self.formatter.format(1299, self.usd) == "$12.99"

    def test_format_usd_large(self) -> None:
        assert self.formatter.format(123456, self.usd) == "$1,234.56"

    def test_format_eur(self) -> None:
        assert self.formatter.format(1299, self.eur) == "12,99 \u20ac"

    def test_format_decimal(self) -> None:
        assert self.formatter.format_decimal(1299, self.usd) == "12.99"
        assert self.formatter.format_decimal(100, self.usd) == "1.00"

    def test_format_zero(self) -> None:
        assert self.formatter.format(0, self.usd) == "$0.00"
