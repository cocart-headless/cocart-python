from __future__ import annotations

from typing import Optional, Protocol


class StorageInterface(Protocol):
    """Protocol for storage adapters used to persist cart keys and tokens."""

    def get(self, key: str) -> Optional[str]: ...

    def set(self, key: str, value: str) -> None: ...

    def delete(self, key: str) -> None: ...
