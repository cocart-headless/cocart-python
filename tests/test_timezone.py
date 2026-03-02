from __future__ import annotations

import pytest

from cocart.timezone import TimezoneHelper

try:
    from zoneinfo import ZoneInfo

    ZoneInfo("UTC")
    _has_tzdata = True
except Exception:
    _has_tzdata = False

needs_tzdata = pytest.mark.skipif(not _has_tzdata, reason="tzdata package not installed")


class TestTimezoneHelper:
    def setup_method(self) -> None:
        self.helper = TimezoneHelper()

    def test_detect_timezone(self) -> None:
        tz = self.helper.detect_timezone()
        assert isinstance(tz, str)
        assert len(tz) > 0

    @needs_tzdata
    def test_convert(self) -> None:
        result = self.helper.convert("2024-01-15T12:00:00", "UTC", "America/New_York")
        assert result == "2024-01-15T07:00:00"

    @needs_tzdata
    def test_convert_summer(self) -> None:
        result = self.helper.convert("2024-07-15T12:00:00", "UTC", "America/New_York")
        assert result == "2024-07-15T08:00:00"

    @needs_tzdata
    def test_convert_reverse(self) -> None:
        result = self.helper.convert("2024-01-15T07:00:00", "America/New_York", "UTC")
        assert result == "2024-01-15T12:00:00"
