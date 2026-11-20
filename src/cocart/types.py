from __future__ import annotations

from typing import Any, Literal

# --- Sort / Filter types ---

StockStatus = Literal["instock", "outofstock", "onbackorder"]
SortOrder = Literal["asc", "desc"]
# The sort orders CoCart accepts. Sort by price with ``price_asc`` or ``price_desc``
# (``price`` is rejected); ``relevance`` and ``rand`` need CoCart Starter.
ProductOrderBy = Literal[
    "date",
    "id",
    "menu_order",
    "include",
    "title",
    "slug",
    "name",
    "alphabetical",
    "reverse_alpha",
    "popularity",
    "sales",
    "rating",
    "review_count",
    "by_stock",
    "on_sale_first",
    "featured_first",
    "price_asc",
    "price_desc",
    "relevance",
    "rand",
]
MainPlugin = Literal["starter", "legacy"]

# --- Event types ---

EventListener = Any  # Callable[[Any], None] — kept loose for flexibility
