from __future__ import annotations

from typing import Callable
from unittest.mock import patch

from packaging.requirements import Requirement

from komodo.pypi_dependencies import PypiDependencies


def fail(*args, **kwargs):
    raise AssertionError()


def patch_fetch_from_pypi(f: Callable[[str, str], list[Requirement]] = fail):
    return patch.object(
        PypiDependencies,
        "_get_requirements_from_pypi",
        new=lambda *args: f(*args[1:]),  # drop self parameter
    )
