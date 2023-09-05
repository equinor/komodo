import os
import sys
from contextlib import contextmanager

import pytest

from komodo.lint_package_status import main as lint_package_status_main

RANDOM_STRING = """
    yaml
"""
INVALID_REPOSITORY_PACKAGE_VERSION_TYPE = """
    zopfli:
      0.3:
        source: pypi
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
    wheel1:
      0.40.0:
        make: pip
        maintainer: scout
    wheel2:
      0.40.0:
        make: pip
        maintainer: scout

"""

INVALID_REPOSITORY_UPPERCASE_PACKAGE_NAME = """
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
    wheel1:
      0.40.0:
        make: pip
        maintainer: scout
    wheel2:
      0.40.0:
        make: pip
        maintainer: scout

"""


INVALID_REPOSITORY_MISSING_WHEEL_PACKAGE = """
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
      0.40.1:
        make: pip
        maintainer: scout
"""

VALID_PACKAGE_STATUS = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: high

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low

"""
VALID_PACKAGE_STATUS_EXTRA_WHEEL_PACKAGE = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: high

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low

    wheel3:
     visibility: public
     maturity: deprecated
     importance: low
"""

INVALID_PACKAGE_STATUS_UPPERCASE_PACKAGE_NAME = """
    ZOPFLI:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: high

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

INVALID_PACKAGE_STATUS_DUPLICATE_PACKAGES = """
    zopfli:
      visibility: private

    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: high

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

INVALID_PACKAGE_STATUS_IDENTIFIER_TYPE = """
    3.4:
      visibilitity: private
    zopfli:
      visibility: private
    setuptools:
      visibility: private
    python:
      visibility: public
      maturity: stable
      importance: high
    wheel:
     visibility: private
    wheel1:
     visibility: public
     maturity: experimental
     importance: medium
    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

VALID_PACKAGE_STATUS_MISSING_VISIBILITY = """
    zopfli:
      unknown_key: null
    setuptools:
      visibility: private
    python:
      visibility: public
      maturity: stable
      importance: high
    wheel:
     visibility: private
    wheel1:
     visibility: public
     maturity: experimental
     importance: medium
    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""
VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_MATURITY = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      importance: high

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""
VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_IMPORTANCE = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_MATURITY_AND_IMPORTANCE = """
    zopfli:
      visibility: private
    setuptools:
      visibility: private
    python:
      visibility: public
    wheel:
     visibility: private
    wheel1:
     visibility: public
     maturity: experimental
     importance: medium
    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

VALID_PACKAGE_STATUS_INVALID_VISIBILITY_OPTION = """
    zopfli:
      visibility: invisible
    setuptools:
      visibility: private
    python:
      visibility: public
      maturity: stable
      importance: high
    wheel:
     visibility: private
    wheel1:
     visibility: public
     maturity: experimental
     importance: medium
    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""


VALID_PACKAGE_STATUS_INVALID_MATURITY_OPTION = """
    zopfli:
      visibility: private
    setuptools:
      visibility: private
    python:
      visibility: public
      maturity: immature
      importance: high
    wheel:
     visibility: private
    wheel1:
     visibility: public
     maturity: experimental
     importance: medium
    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""


VALID_PACKAGE_STATUS_INVALID_IMPORTANCE_OPTION = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: very

    wheel:
     visibility: private

    wheel1:
     visibility: public
     maturity: experimental
     importance: medium

    wheel2:
     visibility: public
     maturity: deprecated
     importance: low
"""

INVALID_PACKAGE_STATUS_MISSING_WHEEL_PACKAGE = """
    zopfli:
      visibility: private

    setuptools:
      visibility: private

    python:
      visibility: public
      maturity: stable
      importance: high
"""


@contextmanager
def does_not_raise():
    yield


def create_tmp_file(file_path: str, file_content: str):
    with open(file_path, mode="w", encoding="utf-8") as tmp_file:
        tmp_file.write(file_content)
    return file_path


@pytest.mark.parametrize(
    "package_status_file_content, repository_file_content, expectation",
    [
        pytest.param(
            VALID_PACKAGE_STATUS, VALID_REPOSITORY, does_not_raise(), id="valid_input"
        ),
        pytest.param(
            VALID_PACKAGE_STATUS,
            RANDOM_STRING,
            pytest.raises(
                AssertionError,
                match=r"does not appear to be a repository file produced by komodo.",
            ),
            id="invalid_yaml_repository_file",
        ),
        pytest.param(
            RANDOM_STRING,
            VALID_REPOSITORY,
            pytest.raises(
                AssertionError,
                match=(
                    r"does not appear to be a package_status file produced by komodo."
                ),
            ),
            id="invalid_yaml_package_status_file",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS,
            INVALID_REPOSITORY_PACKAGE_VERSION_TYPE,
            pytest.raises(
                SystemExit,
                match=r"invalid version type",
            ),
            id="invalid_repository_package_version_type",
        ),
        pytest.param(
            INVALID_PACKAGE_STATUS_IDENTIFIER_TYPE,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit, match=r"Package name .* should be of type string"
            ),
            id="invalid_repository_package_status_identifier_type",
        ),
        pytest.param(
            INVALID_PACKAGE_STATUS_MISSING_WHEEL_PACKAGE,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=(
                    r"packages are specified in the repository file, but not in the"
                    r" package status file: \[(('wheel'|'wheel1'|'wheel2')(, )?){3}"
                ),
            ),
            id="valid_input_package_status_missing_package",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_EXTRA_WHEEL_PACKAGE,
            INVALID_REPOSITORY_MISSING_WHEEL_PACKAGE,
            pytest.raises(
                SystemExit,
                match=(
                    r"packages are specified in the package status file but not in"
                    r" the repository file: \[(('wheel1'|'wheel2'|'wheel3')(, )?){3}"
                ),
            ),
            id="valid_input_repository_missing_package",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_MISSING_VISIBILITY,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match=r"invalid visibility type \(None\)"),
            id="valid_input_package_status_missing_visibility",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_MATURITY,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match=r"invalid maturity type \(None\)"),
            id="valid_input_package_status_public_package_missing_maturity",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_IMPORTANCE,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match=r"invalid importance type \(None\)"),
            id="valid_input_package_status_public_package_missing_importance",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_PUBLIC_VISIBILITY_MISSING_MATURITY_AND_IMPORTANCE,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit,
                match=(
                    r"invalid maturity type \(None\)\n.*invalid importance type"
                    r" \(None\)"
                ),
            ),
            id="valid_input_package_status_package_missing_maturity_and_importance",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_INVALID_VISIBILITY_OPTION,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit, match=r"Package 'zopfli' has invalid visibility value "
            ),
            id="valid_input_package_status_invalid_visibility_option",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_INVALID_MATURITY_OPTION,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit, match=r"Package 'python' has invalid maturity value"
            ),
            id="valid_input_package_status_invalid_maturity_option",
        ),
        pytest.param(
            VALID_PACKAGE_STATUS_INVALID_IMPORTANCE_OPTION,
            VALID_REPOSITORY,
            pytest.raises(
                SystemExit, match=r"python has invalid importance value \(very\)"
            ),
            id="valid_input_package_status_invalid_importance_option",
        ),
        pytest.param(
            INVALID_PACKAGE_STATUS_DUPLICATE_PACKAGES,
            VALID_REPOSITORY,
            pytest.raises(SystemExit, match='found duplicate key "zopfli"'),
            id="invalid_package_status_duplicate_packages",
        ),
    ],
)
def test_integration(
    package_status_file_content: str,
    repository_file_content: str,
    expectation,
    monkeypatch,
    tmpdir,
):
    with tmpdir.as_cwd():
        folder_name = os.path.join(os.getcwd(), "test_package_status/")
        os.makedirs(folder_name)
        repository_file = create_tmp_file(
            f"{folder_name}/test_repository.yml", repository_file_content
        )
        package_status_file = create_tmp_file(
            f"{folder_name}/test_package_status.yml", package_status_file_content
        )
    monkeypatch.setattr(sys, "argv", ["", package_status_file, repository_file])
    with expectation:
        lint_package_status_main()
