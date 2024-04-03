from contextlib import contextmanager
from pathlib import Path

import pytest

from komodo.yaml_file_types import (
    KomodoException,
    PackageStatusFile,
    ReleaseDir,
    ReleaseFile,
    RepositoryFile,
    _komodo_error,
)


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    ("content", "expectations"),
    [
        pytest.param(
            'zopfli: "0.3"\npytest: 0.40.1',
            does_not_raise(),
            id="valid_release_file",
        ),
        pytest.param(
            "zopfli",
            pytest.raises(
                AssertionError,
                match=r"The file you provided does not appear to be a release file",
            ),
            id="invalid_release_file_format",
        ),
        pytest.param(
            'zopfli: "0.3"\nzopfli: "0.3"',
            pytest.raises(SystemExit, match='found duplicate key "zopfli"'),
            id="invalid_release_file_duplicate_packages",
        ),
        pytest.param(
            '1.2: "0.3"\nzopfli: "0.3"',
            pytest.raises(
                SystemExit,
                match=r"Package name .* should be of type string",
            ),
            id="invalid_release_file_float_package_name",
        ),
        pytest.param(
            'zopfli: 0.3\npytest: "0.3"',
            pytest.raises(SystemExit, match=r"Package .* has invalid version.*\(0.3\)"),
            id="invalid_release_file_float_package_version",
        ),
        pytest.param(
            'zopfli:\npytest: "0.3"',
            pytest.raises(
                SystemExit,
                match=r"Package .* has invalid version.*\(None\)",
            ),
            id="invalid_release_file_None_package_version",
        ),
    ],
)
def test_release_file_yaml_type(content, expectations):
    with expectations:
        ReleaseFile().from_yaml_string(content)


@pytest.mark.parametrize(
    "valid",
    (
        "bleeding-py36.yml",
        "/home/anyuser/komodo/2020.01.03-py36-rhel6.yml",
        "myrelease-py36.yml",
        "myrelease-py311.yml",
        "myrelease-py311-rhel8.yml",
        "myrelease-py36-rhel6.yml",
        "myrelease-py36-rhel7.yml",
    ),
)
def test_release_name_valid(valid):
    assert ReleaseFile.lint_release_name(valid) == []


@pytest.mark.parametrize(
    "invalid",
    (
        "bleeding",
        "bleeding.yml",
        "2020.01.01",
        "2020.01.00.yml",
        "/home/anyuser/komodo-releases/releases/2020.01.00.yml",
        "bleeding-py36",
        "bleeding-rhel6.yml",
    ),
)
def test_release_name_invalid(invalid):
    assert ReleaseFile.lint_release_name(invalid) != []


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
VALID_REPOSITORY_ADDITIONAL_UNKNOWN_PROPERTIES = """
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
        added_for: performance
"""
INVALID_REPOSITORY_ADDITIONAL_UNKNOWN_UPPERCASE_PROPERTIES = """
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
        ADDED_FOR: performance
        style: 2.2
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
    python:
      3.9.1:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_DUPLICATE_PACKAGE_VERSIONS = """
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
      3.8.6:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout

    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_FLOAT_PACKAGE_NAME = """
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
    1.2:
      1.20.0:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_FLOAT_PACKAGE_VERSION = """
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
      3.8:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_NONE_PACKAGE_VERSION = """
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
      3.8.1:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
      :
        make: pip
        maintainer: scout
        source: pypi
    wheel:
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
      3.8.2:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_MULTIPLE_ERRORS = """
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
      3.8:
        make: sh
        makefile: build__python-virtualenv.sh
        maintainer: scout
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""
INVALID_REPOSITORY_MISSING_DEPENDENCY = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - setuptools
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
INVALID_REPOSITORY_SOURCE_TYPE = """
    zopfli:
      "0.3":
        source: 1.2
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
INVALID_REPOSITORY_MAKE_TYPE = """
    zopfli:
      "0.3":
        source: pypi
        make: 1.2
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
INVALID_REPOSITORY_MAKE_VALUE = """
    zopfli:
      "0.3":
        source: pypi
        make: cargo
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
INVALID_REPOSITORY_MAINTAINER_TYPE = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: 1.2
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
INVALID_REPOSITORY_DEPENDENCY_TYPE = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
        maintainer: scout
        depends:
          - 1.2
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
INVALID_REPOSITORY_MISSING_MAKE = """
    zopfli:
      "0.3":
        source: pypi
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
INVALID_REPOSITORY_MISSING_MAINTAINER = """
    zopfli:
      "0.3":
        source: pypi
        make: pip
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
INVALID_YAML = "zopfli"


@pytest.mark.parametrize(
    ("content", "expectations"),
    [
        pytest.param(VALID_REPOSITORY, does_not_raise(), id="valid_repository_file"),
        pytest.param(
            INVALID_YAML,
            pytest.raises(
                AssertionError,
                match=r"The file you provided does not appear to be a repository file",
            ),
            id="invalid_repository_file_format",
        ),
        pytest.param(
            INVALID_REPOSITORY_DUPLICATE_PACKAGES,
            pytest.raises(SystemExit, match='found duplicate key "python"'),
            id="invalid_repository_file_duplicate_packages",
        ),
        pytest.param(
            INVALID_REPOSITORY_DUPLICATE_PACKAGE_VERSIONS,
            pytest.raises(SystemExit, match='found duplicate key "3.8.6"'),
            id="invalid_repository_file_duplicate_versions",
        ),
        pytest.param(
            INVALID_REPOSITORY_FLOAT_PACKAGE_NAME,
            pytest.raises(
                SystemExit,
                match=r"Package name .* should be of type string",
            ),
            id="invalid_repository_file_float_package_name",
        ),
        pytest.param(
            INVALID_REPOSITORY_FLOAT_PACKAGE_VERSION,
            pytest.raises(SystemExit, match=r"Package .* has invalid version.*\(3.8\)"),
            id="invalid_repository_file_float_package_version",
        ),
        pytest.param(
            INVALID_REPOSITORY_NONE_PACKAGE_VERSION,
            pytest.raises(SystemExit, match=r"Package .* has invalid version type"),
            id="invalid_repository_file_None_package_version",
        ),
        pytest.param(
            INVALID_REPOSITORY_MISSING_DEPENDENCY,
            pytest.raises(SystemExit, match=r"Dependency .* not found for package"),
            id="invalid_repository_file_dependency_missing",
        ),
        pytest.param(
            INVALID_REPOSITORY_SOURCE_TYPE,
            pytest.raises(
                SystemExit,
                match=r"property \'source\' has invalid property value type",
            ),
            id="invalid_repository_file_float_source",
        ),
        pytest.param(
            INVALID_REPOSITORY_MAKE_TYPE,
            pytest.raises(SystemExit, match=r"Package.*has invalid make type"),
            id="invalid_repository_file_float_make",
        ),
        pytest.param(
            INVALID_REPOSITORY_MAINTAINER_TYPE,
            pytest.raises(SystemExit, match=r"Package.*has invalid maintainer type"),
            id="invalid_repository_file_float_maintainer",
        ),
        pytest.param(
            INVALID_REPOSITORY_DEPENDENCY_TYPE,
            pytest.raises(SystemExit, match=r"Package .* has invalid dependency type"),
            id="invalid_repository_file_float_dependency",
        ),
        pytest.param(
            INVALID_REPOSITORY_MISSING_MAKE,
            pytest.raises(
                SystemExit,
                match=r"Package .* has invalid make type \(None\)",
            ),
            id="invalid_repository_file_missing_make",
        ),
        pytest.param(
            INVALID_REPOSITORY_MISSING_MAINTAINER,
            pytest.raises(
                SystemExit,
                match=r"Package .* has invalid maintainer type \(None\)",
            ),
            id="invalid_repository_file_missing_maintainer",
        ),
        pytest.param(
            INVALID_REPOSITORY_MAKE_VALUE,
            pytest.raises(
                SystemExit,
                match=r"Package.*has invalid make value \(cargo\)",
            ),
            id="invalid_repository_file_invalid_make_value",
        ),
        pytest.param(
            INVALID_REPOSITORY_MULTIPLE_ERRORS,
            pytest.raises(
                SystemExit,
                match=r"Package .* has invalid version type",
            ),
            id="invalid_repository_file_multiple_errors",
        ),
        pytest.param(
            VALID_REPOSITORY_ADDITIONAL_UNKNOWN_PROPERTIES,
            does_not_raise(),
            id="valid_repository_file_additional_unknown_properties",
        ),
        pytest.param(
            INVALID_REPOSITORY_ADDITIONAL_UNKNOWN_UPPERCASE_PROPERTIES,
            pytest.raises(
                SystemExit,
                match=(r"invalid property value type \(2.2\).*"),
            ),
            id="invalid_repository_file_additional_unknown_uppercase_properties",
        ),
    ],
)
def test_repository_file_yaml_type(content, expectations):
    with expectations:
        RepositoryFile().from_yaml_string(content)


LINT_MAINTAINER_TEST_REPO = """
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
      '3.9':
        maintainer: scout
        makefile: build__python-virtualenv.sh
        make: pip
    wheel:
      0.40.0:
        make: pip
        maintainer: scout
"""


@pytest.mark.parametrize(
    ("package_name", "package_version", "expectation", "return_object"),
    [
        pytest.param(
            "python",
            "3.8.6",
            does_not_raise(),
            _komodo_error("python", "3.8.6", "scout"),
            id="lint_maintainer_returns_valid",
        ),
        pytest.param(
            "pytest",
            "3.9",
            pytest.raises(KomodoException),
            None,
            id="lint_maintainer_throws_on_missing_package",
        ),
        pytest.param(
            "python",
            "4.0",
            pytest.raises(KomodoException),
            None,
            id="lint_maintainer_throws_on_missing_package",
        ),
    ],
)
def test_repository_file_lint_maintainer(
    package_name,
    package_version,
    expectation,
    return_object,
):
    repo_file = RepositoryFile().from_yaml_string(LINT_MAINTAINER_TEST_REPO)
    with expectation:
        result = repo_file.lint_maintainer(package_name, package_version)
    if return_object:
        assert result == return_object


@pytest.mark.parametrize(
    ("package_status_file_content", "expectation"),
    [
        pytest.param(
            "python:\n  visibility: public\n  maturity: experimental\n  importance:"
            " high",
            does_not_raise(),
            id="valid_package_status",
        ),
        pytest.param(
            "0.2:\n  visibility: public\n  maturity: experimental\n  importance: high",
            pytest.raises(SystemExit, match=r"should be of type string"),
            id="invalid_package_status__float_package_name",
        ),
        pytest.param(
            "python:\n  maturity: important",
            pytest.raises(SystemExit, match=r"invalid visibility type"),
            id="invalid_package_status__missing_visibility",
        ),
        pytest.param(
            "python:\n  visibility: private",
            does_not_raise(),
            id="valid_package_status__private_visibility",
        ),
        pytest.param(
            "python:\n  visibility: hidden\n  maturity: experimental\n  importance:"
            " high",
            pytest.raises(SystemExit, match=r"invalid visibility value"),
            id="invalid_package_status__invalid_visibility_value",
        ),
        pytest.param(
            "python:\n  visibility: public\n  importance: high",
            pytest.raises(SystemExit, match=r"invalid maturity type"),
            id="invalid_package_status__public_visibility_missing_maturity",
        ),
        pytest.param(
            "python:\n  visibility: public\n  maturity: experimental\n",
            pytest.raises(SystemExit, match=r"invalid importance type"),
            id="invalid_package_status__public_visibility_missing_importance",
        ),
        pytest.param(
            "python:\n  visibility: public\n  maturity: immature\n  importance: high",
            pytest.raises(SystemExit, match=r"invalid maturity value"),
            id="invalid_package_status__public_visibility_invalid_maturity",
        ),
        pytest.param(
            "python:\n  visibility: public\n  maturity: experimental\n  importance:"
            " extremely",
            pytest.raises(SystemExit, match=r"invalid importance value"),
            id="invalid_package_status__public_visibility_invalid_importance",
        ),
        pytest.param(
            "python:\n  visibility: public\n  maturity: immature\n  importance:"
            " extremely",
            pytest.raises(
                SystemExit,
                match=r"invalid maturity value.*\n.*invalid importance value",
            ),
            id="invalid_package_status__multiple_errors",
        ),
    ],
)
def test_package_status_file_type(package_status_file_content: str, expectation):
    with expectation:
        PackageStatusFile().from_yaml_string(package_status_file_content)


def test_release_dir_with_one_release(tmpdir):
    with tmpdir.as_cwd():
        Path("releases").mkdir()
        Path("releases/somerelease.yml").write_text("foo: 0.4.1", encoding="utf-8")
        assert ReleaseDir()("releases") == {"somerelease": {"foo": "0.4.1"}}


def test_release_dir_with_two_releases(tmpdir):
    with tmpdir.as_cwd():
        Path("releases").mkdir()
        Path("releases/somerelease.yml").write_text("foo: 0.4.1", encoding="utf-8")
        Path("releases/anotherrelease.yml").write_text("bar: 1.4.1", encoding="utf-8")
        assert ReleaseDir()("releases") == {
            "somerelease": {"foo": "0.4.1"},
            "anotherrelease": {"bar": "1.4.1"},
        }
