import os
import sys
from contextlib import contextmanager

import pytest

from komodo.lint_upgrade_proposals import main as lint_main


def _write_file(file_path: str, file_content: str) -> str:
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(file_content)
    return file_path


def _create_tmp_test_files(
    upgrade_proposals_content,
    repository_file_content,
) -> (str, str):
    folder_name = os.path.join(os.getcwd(), "test_lint_upgrade_proposals/")
    os.mkdir(folder_name)
    upgrade_proposals_file = _write_file(
        f"{folder_name}/upgrade_proposals.yml",
        upgrade_proposals_content,
    )
    repository_file = _write_file(
        f"{folder_name}/repository.yml",
        repository_file_content,
    )
    return (upgrade_proposals_file, repository_file)


@contextmanager
def does_not_raise():
    yield


VALID_REPOSITORY = """
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


REPOSITORY_FILE_MISSING_PACKAGE = """
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
REPOSITORY_FILE_MISSING_PACKAGE_VERSION = """
    setuptools:
      68.0.0:
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - wheel
          - python
    python:
      3.9.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""

VALID_UPGRADE_PROPOSALS = """
1111-11:
1111-12:
  python: 3.8.6
"""
VALID_EMPTY_UPGRADE_PROPOSALS = """
1111-11:
1111-12:
"""
VALID_UPGRADE_PROPOSALS_MULTIPLE_RELEASES = """
1111-11:
  wheel: 0.40.0
1111-12:
  python: 3.8.6
"""
INVALID_UPGRADE_PROPOSALS_DUPLICATE_PACKAGES = """
1111-11:
1111-12:
  python: 3.8.6
  pytest: "0.41"
  python: 3.8.9
"""
INVALID_UPGRADE_PROPOSALS_DUPLICATE_PACKAGES_AND_VERSIONS = """
1111-11:
1111-12:
  python: 3.8.6
  pytest: "0.41"
  python: 3.8.6
"""
INVALID_UPGRADE_PROPOSALS_MULTIPLE_ERRORS = """
1111-11:
1111-12:
  python: 3.8.6
  pytest: "0.40"
  nonexistentlib: 0.0.1
"""

INVALID_UPGRADE_PROPOSALS_FLOAT_PACKAGE_NAME = """
1111-11:
1111-12:
  3.9: None
"""

INVALID_UPGRADE_PROPOSALS_FLOAT_PACKAGE_VERSION = """
1111-11:
1111-12:
  python: 3.9
"""

RANDOM_STRING = """
yaml
"""


@pytest.mark.parametrize(
    ("upgrade_proposals_content", "repository_file_content", "expectation"),
    [
        pytest.param(
            VALID_UPGRADE_PROPOSALS,
            VALID_REPOSITORY,
            does_not_raise(),
            id="valid_input_files",
        ),
        pytest.param(
            INVALID_UPGRADE_PROPOSALS_MULTIPLE_ERRORS,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=r"(pytest.*\n.*nonexistentlib)|(nonexistentlib.*\n.*pytest)",
            ),
            id="invalid_upgrade_proposals_multiple_errors",
        ),
        pytest.param(
            VALID_UPGRADE_PROPOSALS,
            RANDOM_STRING,
            pytest.raises(
                AssertionError,
                match=("does not appear to be a repository file"),
            ),
            id="invalid_repository_file_format",
        ),
        pytest.param(
            RANDOM_STRING,
            VALID_REPOSITORY,
            pytest.raises(
                AssertionError,
                match=("does not appear to be an upgrade_proposals file"),
            ),
            id="invalid_upgrade_proposals_file_format",
        ),
        pytest.param(
            VALID_EMPTY_UPGRADE_PROPOSALS,
            VALID_REPOSITORY,
            does_not_raise(),
            id="no_upgrades_in_upgrade_proposals",
        ),
        pytest.param(
            VALID_UPGRADE_PROPOSALS_MULTIPLE_RELEASES,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=r"Found upgrades for more than one release",
            ),
            id="upgrades_in_multiple_releases_in_upgrade_proposals",
        ),
        pytest.param(
            VALID_UPGRADE_PROPOSALS,
            REPOSITORY_FILE_MISSING_PACKAGE,
            pytest.raises(
                SystemExit,
                match=r"Dependency 'python' not found for package 'setuptools'",
            ),
            id="repository_file_missing_package",
        ),
        pytest.param(
            VALID_UPGRADE_PROPOSALS,
            REPOSITORY_FILE_MISSING_PACKAGE_VERSION,
            pytest.raises(
                SystemExit,
                match=r"Version '3.8.6' of package 'python' not found in repository",
            ),
            id="repository_file_missing_package_version",
        ),
        pytest.param(
            INVALID_UPGRADE_PROPOSALS_DUPLICATE_PACKAGES,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match='found duplicate key "python"'),
            id="upgrade_proposals_duplicate_packages",
        ),
        pytest.param(
            INVALID_UPGRADE_PROPOSALS_DUPLICATE_PACKAGES_AND_VERSIONS,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match='found duplicate key "python"'),
            id="upgrade_proposals_duplicate_packages_and_versions",
        ),
        pytest.param(
            INVALID_UPGRADE_PROPOSALS_FLOAT_PACKAGE_NAME,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=(
                    r"Package name \(3.9\) should be of type string.*\n.*does not"
                    r" appear to be an upgrade_proposals file"
                ),
            ),
            id="invalid_upgrade_proposals_float_package_name",
        ),
        pytest.param(
            INVALID_UPGRADE_PROPOSALS_FLOAT_PACKAGE_VERSION,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=r"invalid version type",
            ),
            id="invalid_upgrade_proposals_float_package_version",
        ),
    ],
)
def test_lint(
    upgrade_proposals_content: str,
    repository_file_content: str,
    expectation,
    monkeypatch,
    tmpdir,
):
    with tmpdir.as_cwd():
        (upgrade_proposals_file, repository_file) = _create_tmp_test_files(
            upgrade_proposals_content,
            repository_file_content,
        )

    monkeypatch.setattr(sys, "argv", ["", upgrade_proposals_file, repository_file])
    with expectation:
        lint_main()
