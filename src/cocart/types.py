from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing import Literal

# --- Sort / Filter types ---

StockStatus = Literal["instock", "outofstock", "onbackorder"]
SortOrder = Literal["asc", "desc"]
ProductOrderBy = Literal["date", "id", "include", "title", "slug", "price", "popularity", "rating"]
MainPlugin = Literal["basic", "legacy"]

# --- Event types ---

EventListener = Any  # Callable[[Any], None] — kept loose for flexibility
