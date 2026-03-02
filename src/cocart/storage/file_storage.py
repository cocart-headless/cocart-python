from __future__ import annotations

import hashlib
import os
from typing import Optional


class FileStorage:
    """File-based storage adapter for persisting cart keys and tokens."""

    def __init__(self, directory: str) -> None:
        self._directory = directory
        os.makedirs(directory, exist_ok=True)

    def get(self, key: str) -> Optional[str]:
        path = self._get_file_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def set(self, key: str, value: str) -> None:
        with open(self._get_file_path(key), "w", encoding="utf-8") as f:
            f.write(value)

    def delete(self, key: str) -> None:
        path = self._get_file_path(key)
        if os.path.exists(path):
            os.remove(path)

    def _get_file_path(self, key: str) -> str:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self._directory, f"{hashed}.txt")
