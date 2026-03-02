from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class HttpResponse:
    """Raw HTTP response from an adapter."""

    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
