from __future__ import annotations

import os
import sys
from textwrap import dedent
from typing import Any, Callable
from unittest.mock import patch

import pytest
from packaging.requirements import Requirement

from komodo import lint as kmdlint
from komodo.komodo_error import KomodoError
from komodo.pypi_dependencies import PypiDependencies
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def lint(
    release: dict[str, str],
    repository: dict[str, Any],
) -> kmdlint.Report:
    return kmdlint.lint(
        ReleaseFile.from_dictionary(release),
        RepositoryFile.from_dictionary(repository),
    )


def test_lint():
    lint_report = lint(
        {
            "python": "v3.14",
            "requests": "8.18.4",
        },
        {
            "python": {
                "v3.14": {
                    "maintainer": "ertomatic@equinor.com",
                    "make": "sh",
                    "makefile": "configure",
                    "source": "git://github.com/python/cpython.git",
                },
            },
            "requests": {
                "8.18.4": {
                    "depends": ["python"],
                    "maintainer": "maintainer@equinor.com",
                    "make": "pip",
                    "source": "pypi",
                },
            },
            "secrettool": {
                "10.0": {
                    "source": "https://{{ACCESS_TOKEN}}@github.com/equinor/secrettool.git",
                    "fetch": "git",
                    "make": "pip",
                    "maintainer": "Prop Rietary",
                },
            },
        },
    )
    assert lint_report.version_errors == []


def test_lint_empty_release_has_no_errors():
    lint_report = lint(
        {},
        {
            "python": {
                "v3.14": {
                    "maintainer": "ertomatic@equinor.com",
                    "make": "sh",
                    "makefile": "configure",
                    "source": "git://github.com/python/cpython.git",
                },
            },
        },
    )
    assert lint_report.version_errors == []
    assert lint_report.maintainer_errors == []
    assert lint_report.release_name_errors == []


def test_missing_repo_package_gives_error():
    lint_report = lint({"python": "3.14.0"}, {})
    assert lint_report.version_errors == []
    assert lint_report.maintainer_errors == [
        KomodoError(
            package="python",
            version="3.14.0",
            maintainer=None,
            depends=None,
            err="Package 'python' not found in repository",
        )
    ]
    assert lint_report.release_name_errors == []


def _write_file(file_path: str, file_content: str) -> str:
    with open(file_path, mode="w", encoding="utf-8") as file_stream:
        file_stream.write(file_content)
    return file_path


def _create_tmp_test_files(
    release_file_content, repository_file_content
) -> tuple[str, str]:
    folder_name = os.path.join(os.getcwd(), "test_lint/")
    os.mkdir(folder_name)
    release_file = _write_file(
        f"{folder_name}/2020.02.08-py27.yml",
        release_file_content,
    )
    repository_file = _write_file(
        f"{folder_name}/repository.yml",
        repository_file_content,
    )
    return (release_file, repository_file)


YAML_FILE = """
    yaml:
"""
VALID_REPOSITORY = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
          - python
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""

INVALID_REPOSITORY__FLOAT_VERSION = """
    zopfli:
      0.3:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
          - python
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY__MISSING_PACKAGE = """
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_DUPLICATE_PACKAGES = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
          - python
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
          - python
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""

INVALID_REPOSITORY_FILE_UPPERCASE_PACKAGES = """
    ZOPFLI:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
          - python
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""

VALID_RELEASE_FILE = 'zopfli:  "0.3"\nwheel: 0.40.0\npython: 3.8.6\nsetuptools: 68.0.0'
INVALID_RELEASE_FILE_DUPLICATE_PACKAGES = (
    'zopfli:  "0.3"\nzopfli:  "0.4"\nwheel: 0.40.0\npython: 3.8.6\nsetuptools: 68.0.0'
)
INVALID_RELEASE_FILE_UPPERCASE_PACKAGES = (
    'ZOPFLI:  "0.3"\nwheel: 0.40.0\npython: 3.8.6\nsetuptools: 68.0.0'
)
INVALID_RELEASE_FILE = "zopfli:  0.3\nwheel: 0.40.0\npython: 3.8.6\nsetuptools:"
RANDOM_STRING = "slipstipsripsogandrebuskvekster"
SYSTEM_EXIT_OK_CODE = "0"
SYSTEM_EXIT_KOMODO_ERROR = "Error in komodo configuration"

INVALID_RELEASE_FILE_MISSING_DEPENDENCY_NEEDED_IN_REPOSITORY = (
    'zopfli:  "0.3"\nwheel: 0.40.0\nsetuptools: 68.0.0'
)


@pytest.mark.parametrize(
    ("release_file_content", "repository_file_content", "expectation"),
    [
        pytest.param(
            VALID_RELEASE_FILE,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match=SYSTEM_EXIT_OK_CODE),
            id="valid_input",
        ),
        pytest.param(
            "zopfli:  0.3\nwheel: 0.40.0\npython: 3.8.6\nsetuptools: 68.0.0",
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=(
                    r"Package .* has invalid version.*\n.*does not appear to be a"
                    r" release file"
                ),
            ),
            id="invalid_input_release_file_version_type_float",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            INVALID_REPOSITORY__FLOAT_VERSION,
            pytest.raises(
                SystemExit,
                match=r"Package 'zopfli' has invalid version type \(0.3\)",
            ),
            id="invalid_input_repository_file_version_type_float",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            INVALID_REPOSITORY__MISSING_PACKAGE,
            pytest.raises(SystemExit, match=SYSTEM_EXIT_KOMODO_ERROR),
            id="invalid_input_repository_file_missing_package",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            YAML_FILE,
            pytest.raises(
                SystemExit,
                match=(
                    r"Versions of package .* is not formatted correctly"
                    r" \(.*\).*\n.*does not appear to be a repository file"
                ),
            ),
            id="invalid_input_repository_file_format",
        ),
        pytest.param(
            YAML_FILE,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=(
                    r"Package .* has invalid version type \(None\).*\n.*does not"
                    r" appear to be a release file"
                ),
            ),
            id="invalid_input_release_file_format",
        ),
        pytest.param(
            RANDOM_STRING,
            VALID_REPOSITORY,
            pytest.raises(
                AssertionError,
                match=r"does not appear to be a release file produced by komodo",
            ),
            id="invalid_input_release_type",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            RANDOM_STRING,
            pytest.raises(
                AssertionError,
                match=r"does not appear to be a repository file produced by komodo",
            ),
            id="invalid_input_repository_type",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            INVALID_REPOSITORY_DUPLICATE_PACKAGES,
            pytest.raises(SystemExit, match='found duplicate key "zopfli"'),
            id="invalid_input_repository_duplicate_packages",
        ),
        pytest.param(
            INVALID_RELEASE_FILE_DUPLICATE_PACKAGES,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match='found duplicate key "zopfli"'),
            id="invalid_input_release_file_duplicate_packages",
        ),
        pytest.param(
            INVALID_RELEASE_FILE_UPPERCASE_PACKAGES,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=SYSTEM_EXIT_KOMODO_ERROR,
            ),
            id="invalid_input_release_file_uppercase_package",
        ),
        pytest.param(
            VALID_RELEASE_FILE,
            INVALID_REPOSITORY_FILE_UPPERCASE_PACKAGES,
            pytest.raises(
                SystemExit,
                match=SYSTEM_EXIT_KOMODO_ERROR,
            ),
            id="invalid_input_repository_file_uppercase_package",
        ),
        pytest.param(
            INVALID_RELEASE_FILE_MISSING_DEPENDENCY_NEEDED_IN_REPOSITORY,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
            ),
            id="invalid_release_file_missing_dependency_needed_in_repository",
        ),
    ],
)
def test_integration_main(
    release_file_content,
    repository_file_content,
    expectation,
    monkeypatch,
    tmpdir,
):
    with tmpdir.as_cwd():
        (release_file, repository_file) = _create_tmp_test_files(
            release_file_content,
            repository_file_content,
        )
    monkeypatch.setattr(sys, "argv", ["", release_file, repository_file])
    with expectation:
        kmdlint.lint_main()


def fail(*args, **kwargs):
    raise AssertionError()


def patch_fetch_from_pypi(f: Callable[[str, str], list[Requirement]] = fail):
    return patch.object(
        PypiDependencies,
        "_get_requirements_from_pypi",
        new=lambda *args: f(*args[1:]),  # drop self parameter
    )


def test_missing_dependency_is_printed(tmp_path, monkeypatch, capsys):
    (tmp_path / "builtin_python_versions.yml").write_text("3.11-builtin: 3.11.5\n")
    (release_file := tmp_path / "2025.02.00-py311-rhel9.yml").write_text(
        dedent("""\
        python: 3.11-builtin\n
        ert: 13.0.0
        """)
    )
    (repo_file := tmp_path / "repo.yml").write_text(
        dedent("""\
        ert:
          13.0.0:
            maintainer: scout
            make: pip
            source: pypi
        python:
          3.11-builtin:
            maintainer: scout
            make: sh
            makefile: build__python-virtualenv.sh
            makeopts: --virtualenv-interpreter /usr/bin/python3.11
        """)
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match=SYSTEM_EXIT_KOMODO_ERROR):
        with patch_fetch_from_pypi(lambda *_: [Requirement("numpy < 2")]):
            kmdlint.lint_main(
                [str(release_file), str(repo_file), "--check-pypi-dependencies"]
            )
        assert "Failed requirements:\nert\n  numpy<2" in capsys.readouterr()


def check_dependencies(
    release: dict[str, str],
    repository: dict[str, Any],
    full_python_version: str = "3.11.5",
):
    return kmdlint.check_dependencies(
        ReleaseFile.from_dictionary(release),
        RepositoryFile.from_dictionary(repository),
        full_python_version,
    )


@patch_fetch_from_pypi()
def test_empty_depends_field_means_no_dependencies():
    assert (
        check_dependencies(
            {"ert": "13.0.0"},
            {
                "ert": {
                    "13.0.0": {"source": "git", "make": "pip", "maintainer": "scout"}
                }
            },
        )
        == []
    )


def test_empty_depends_field_means_no_dependencies_in_transient():
    def pypi_requirements(package, _):
        # we only expect to fetch
        # semeio from pypi in the below setup
        assert package == "semeio"
        return [Requirement("ert>=13.0.0")]

    with patch_fetch_from_pypi(pypi_requirements):
        assert (
            check_dependencies(
                {"ert": "main", "semeio": "0.1.0"},
                {
                    "ert": {
                        "main": {"source": "git", "make": "pip", "maintainer": "scout"}
                    },
                    "semeio": {
                        "0.1.0": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        }
                    },
                },
            )
            == []
        )
