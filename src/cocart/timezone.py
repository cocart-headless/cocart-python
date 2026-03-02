from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class TimezoneHelper:
    """Utility for timezone detection and conversion."""

    def detect_timezone(self) -> str:
        """Detect the system timezone."""
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, "key"):
            return str(local_tz.key)  # type: ignore[union-attr]
        return str(local_tz)

    def convert(self, date_string: str, from_tz: str, to_tz: str) -> str:
        """Convert an ISO date string between timezones.

        Args:
            date_string: ISO 8601 date string.
            from_tz: Source timezone name (e.g. "UTC").
            to_tz: Target timezone name (e.g. "America/New_York").

        Returns:
            Converted date string in ISO format.
        """
        from_zone = ZoneInfo(from_tz)
        to_zone = ZoneInfo(to_tz)
        dt = datetime.fromisoformat(date_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=from_zone)
        result = dt.astimezone(to_zone)
        return result.strftime("%Y-%m-%dT%H:%M:%S")

    def to_local(self, date_string: str, store_tz: str = "UTC") -> str:
        """Convert a date string from the store timezone to local time.

        Args:
            date_string: ISO 8601 date string in the store timezone.
            store_tz: The store's timezone (default: "UTC").

        Returns:
            Date string converted to the local system timezone.
        """
        return self.convert(date_string, store_tz, self.detect_timezone())
