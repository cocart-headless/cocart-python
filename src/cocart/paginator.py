from __future__ import annotations

from typing import Callable, Iterator, List

from cocart.response import Response


class Paginator:
    """Iterator that automatically paginates through API results.

    Example::

        for page in client.products().all_paginated(per_page=20):
            print(page.to_dict())

        # Or collect all pages
        pages = client.products().all_paginated(per_page=50).to_list()
    """

    def __init__(
        self,
        fetch_page: Callable[[int], Response],
        start_page: int = 1,
    ) -> None:
        self._fetch_page = fetch_page
        self._start_page = start_page

    def __iter__(self) -> Iterator[Response]:
        page = self._start_page
        while True:
            response = self._fetch_page(page)
            yield response
            total_pages = response.get_total_pages()
            if total_pages is None or page >= total_pages:
                break
            page += 1

    def to_list(self) -> List[Response]:
        """Collect all pages into a list."""
        return list(self)
