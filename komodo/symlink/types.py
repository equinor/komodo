from __future__ import annotations

from typing import Mapping, Sequence, TypedDict


class LinkDict(TypedDict):
    root_folder: str
    root_links: Sequence[str]
    links: Mapping[str, str]
