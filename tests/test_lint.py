import os
import sys

import pytest
import yaml

from komodo import lint
from komodo.yaml_file_types import ReleaseFile, RepositoryFile

REPO = {
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
}

RELEASE = {
    "python": "v3.14",
    "requests": "8.18.4",
}


def test_lint():
    repo = RepositoryFile().from_yaml_string(value=yaml.safe_dump(REPO))
    release = ReleaseFile().from_yaml_string(value=yaml.safe_dump(RELEASE))
    lint_report = lint.lint(release, repo)
    assert lint_report.dependencies == []
    assert lint_report.versions == []


def _write_file(file_path: str, file_content: str) -> str:
    with open(file_path, mode="w", encoding="utf-8") as file_stream:
        file_stream.write(file_content)
    return file_path


def _create_tmp_test_files(release_file_content, repository_file_content) -> (str, str):
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
        lint.lint_main()
