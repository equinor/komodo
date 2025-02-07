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


def test_empty_package_lists_have_no_failed_requirements():
    dependencies = PypiDependencies({}, python_version="3.8", cachefile=None)
    assert not dependencies.failed_requirements()


def test_missing_pypi_dependencies_are_reported():
    from_pypi = {("ert", "13.0.0"): [Requirement("numpy==2.0.0")]}
    with patch_fetch_from_pypi(lambda *args: from_pypi[tuple(args)]):
        dependencies = PypiDependencies(
            {"ert": "13.0.0"}, python_version="3.8", cachefile=None
        )
        assert dependencies.failed_requirements() == {
            Requirement("numpy==2.0.0"): "ert"
        }


def test_user_specified_dependencies_are_checked_before_pypi():
    with patch_fetch_from_pypi():
        dependencies = PypiDependencies(
            {"ert": "13.0.0"}, python_version="3.8", cachefile=None
        )
        dependencies.add_user_specified("ert", ["numpy==2.0.0"])
        assert dependencies.failed_requirements() == {
            Requirement("numpy==2.0.0"): "ert"
        }
