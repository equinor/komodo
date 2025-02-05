from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KomodoError:
    package: str | None = None
    version: str | None = None
    maintainer: str | None = None
    depends: list[str] | None = None
    err: str | None = None


class KomodoException(Exception):
    def __init__(self, error_message: KomodoError) -> None:
        self.error = error_message
