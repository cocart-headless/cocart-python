from __future__ import annotations

import os
import tempfile

import pytest

from cocart.storage.file_storage import FileStorage
from cocart.storage.memory_storage import MemoryStorage


class TestMemoryStorage:
    def test_get_set(self) -> None:
        s = MemoryStorage()
        assert s.get("key") is None
        s.set("key", "value")
        assert s.get("key") == "value"

    def test_delete(self) -> None:
        s = MemoryStorage()
        s.set("key", "value")
        s.delete("key")
        assert s.get("key") is None

    def test_delete_nonexistent(self) -> None:
        s = MemoryStorage()
        s.delete("nonexistent")  # Should not raise


class TestFileStorage:
    def test_get_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            s = FileStorage(tmpdir)
            assert s.get("key") is None
            s.set("key", "value")
            assert s.get("key") == "value"

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            s = FileStorage(tmpdir)
            s.set("key", "value")
            s.delete("key")
            assert s.get("key") is None

    def test_delete_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            s = FileStorage(tmpdir)
            s.delete("nonexistent")  # Should not raise

    def test_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "storage")
            s = FileStorage(path)
            s.set("key", "value")
            assert s.get("key") == "value"
