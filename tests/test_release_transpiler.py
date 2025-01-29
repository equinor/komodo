import os
from contextlib import contextmanager

import pytest
import yaml

from komodo.release_transpiler import (
    detect_custom_coordinates,
    transpile_releases,
    transpile_releases_for_pip,
)
from tests import _get_test_root


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    "matrix",
    [
        ({"py": ["3.8"], "rhel": ["7"]}),
        ({"py": ["3.8", "3.11"], "rhel": ["7", "8"]}),
    ],
)
def test_transpile_add_argument(tmpdir, matrix):
    release_file = os.path.join(_get_test_root(), "data", "test_release_matrix.yml")
    release_base = os.path.basename(release_file).strip(".yml")
    with tmpdir.as_cwd():
        transpile_releases(release_file, os.getcwd(), matrix)
        for rhel_coordinate in matrix["rhel"]:
            rhel_coordinate_filename_format = f"rhel{rhel_coordinate}"
            for py_coordinate in matrix["py"]:
                py_coordinate_filename_format = f"py{py_coordinate.replace('.', '')}"
                assert os.path.isfile(
                    f"{release_base}-{py_coordinate_filename_format}-{rhel_coordinate_filename_format}.yml"
                )


@pytest.mark.parametrize(
    ("matrix", "expectation"),
    [
        ({"py": ["3.8"], "rhel": ["8"], "numpy": ["1"]}, does_not_raise()),
        ({"py": ["3.11"], "rhel": ["9"], "numpy": ["2"]}, does_not_raise()),
        (
            {"py": ["3.8", "3.11"], "rhel": ["8", "9"], "numpy": ["1", "2"]},
            does_not_raise(),
        ),
        ({"py": ["3.8", "3.11"], "rhel": ["8", "9"]}, pytest.raises(KeyError)),
        (
            {"py": ["3.8", "3.11"], "rhel": ["8", "9"], "numpy": ["3"]},
            pytest.raises(KeyError),
        ),
    ],
)
def test_transpile_custom_coordinate_releases(tmpdir, matrix, expectation):
    release_file = os.path.join(
        _get_test_root(), "input", "test_custom_coordinate_release.yml"
    )
    release_base = os.path.basename(release_file).strip(".yml")

    packages = ["parcel", "letter", "box", "case"]
    keywords = ["rhel", "py", "numpy"]

    with tmpdir.as_cwd(), expectation:
        transpile_releases(release_file, os.getcwd(), matrix)

        for rhel_coordinate in matrix["rhel"]:
            rhel_coordinate_filename_format = f"rhel{rhel_coordinate}"
            for py_coordinate in matrix["py"]:
                py_coordinate_filename_format = f"py{py_coordinate.replace('.', '')}"
                for custom_coordinate in matrix["numpy"]:
                    custom_coordinate_filename_format = f"numpy{custom_coordinate}"

                    release_file = f"{release_base}-{py_coordinate_filename_format}-{rhel_coordinate_filename_format}-{custom_coordinate_filename_format}.yml"
                    assert os.path.isfile(release_file)
                    with open(release_file, encoding="utf-8") as file:
                        content = yaml.safe_load(file)

                        for p in packages:
                            assert p in content
                        for k in keywords:
                            assert k not in content


def test_automatic_custom_coordinate_detection():
    release_file = os.path.join(
        _get_test_root(), "input", "test_custom_coordinate_release.yml"
    )

    coords = detect_custom_coordinates(release_file)
    assert coords == {"numpy": ["1", "2"]}


@pytest.mark.parametrize(
    ("matrix", "error_message_content"),
    [
        ({"py": ["3.8"], "rhel": ["7"]}, "Test passes, no error reported"),
        (
            {"py": ["3.7"], "rhel": ["7"]},
            ["py37", "rhel7", "lib1"],
        ),
        (
            {"py": ["3.6"], "rhel": ["5"]},
            ["rhel5", "lib1"],
        ),
        (
            {"py": ["3.6"], "rhel": ["7"], "numpy": ["2"]},
            ["numpy2", "lib1"],
        ),
    ],
    ids=["Pass for all packages", "Fail", "Fail", "Missing custom numpy coordinate"],
)
def test_check_version_exists_for_coordinates(matrix, error_message_content, tmpdir):
    release_file = os.path.join(_get_test_root(), "data", "test_release_matrix.yml")
    try:
        with tmpdir.as_cwd():
            transpile_releases(release_file, os.getcwd(), matrix)
    except KeyError as exception_info:
        assert all(word in str(exception_info.args) for word in error_message_content)


def test_transpile_for_pip(tmpdir):
    release_file = os.path.join(_get_test_root(), "data", "test_release_matrix.yml")
    repo_file = os.path.join(_get_test_root(), "data", "test_repository.yml")
    release_base = os.path.basename(release_file).strip(".yml")
    not_pip_pkg = "lib3"
    expected_line = "lib2==2.3.4"
    versions_matrix = {"rhel": ["7"], "py": ["38"]}
    with tmpdir.as_cwd():
        transpile_releases_for_pip(
            release_file,
            os.getcwd(),
            repo_file,
            versions_matrix,
        )
        for rhel_ver in ("rhel7",):
            for py_ver in ("py38",):
                filename = f"{release_base}-{py_ver}-{rhel_ver}.req"
                assert os.path.isfile(filename)
                with open(filename, encoding="utf-8") as fil:
                    file_lines = fil.read().splitlines()
                assert all(not line.startswith(not_pip_pkg) for line in file_lines)
                assert expected_line in file_lines
