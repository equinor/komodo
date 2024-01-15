import os

import pytest
import yaml

from komodo.release_transpiler import (
    build_matrix_file,
    get_py_coords,
    transpile_releases,
    transpile_releases_for_pip,
)
from tests import _get_test_root

builtins = {
    "lib1": {
        "rhel6": {"py27": "0.1.2", "py36": "1.2.3", "py38": "1.2.4"},
        "rhel7": {
            "py27": "0.1.2+builtin",
            "py36": "1.2.3+builtin",
            "py38": "1.2.3+builtin",
        },
    },
}


@pytest.mark.parametrize(
    ("py_coords_input", "packages_lib2", "py_coords_not_in_lib3"),
    [
        (["3.6", "3.8"], "2.3.4", "py27"),
        (None, {"py27": "1.2.3", "py36": "2.3.4", "py38": "2.3.4"}, [""]),
    ],
)
def test_build_release_matrix_py_coords(
    tmpdir,
    py_coords_input,
    packages_lib2,
    py_coords_not_in_lib3,
):
    """lib1 tests packages with builtins,
    lib2 tests packages with same version for two py coordinates,
    lib3 tests packages with different versions for each py coordinate.
    """
    release_base = "2020.01.a1"
    release_folder = os.path.join(_get_test_root(), "data/test_releases/")
    with tmpdir.as_cwd():
        build_matrix_file(release_base, release_folder, builtins, py_coords_input)
        new_release_file = f"{release_base}.yml"
        assert os.path.isfile(new_release_file)
        with open(new_release_file, encoding="utf-8") as new_release_file_stream:
            release_matrix = yaml.safe_load(new_release_file_stream)

        assert release_matrix["lib1"] == builtins["lib1"]
        assert release_matrix["lib2"] == packages_lib2
        assert all(
            py_coordinate not in list(release_matrix["lib3"].keys())
            for py_coordinate in py_coords_not_in_lib3
        )


@pytest.mark.parametrize(
    "matrix",
    [({"py": ["3.8"], "rhel": ["7"]}), ({"py": ["3.8", "3.10"], "rhel": ["7", "8"]})],
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
    ],
    ids=["Pass for all packages", "Fail", "Fail"],
)
def test_check_version_exists_for_coordinates(matrix, error_message_content):
    release_file = os.path.join(_get_test_root(), "data", "test_release_matrix.yml")
    try:
        transpile_releases(release_file, os.getcwd(), matrix)
    except KeyError as exception_info:
        assert all(word in str(exception_info) for word in error_message_content)


def test_get_py_coords():
    release_folder = os.path.join(_get_test_root(), "data", "test_releases")
    release_base = "2020.01.a1"
    py_coords = get_py_coords(release_base, release_folder)
    assert py_coords == ["py27", "py36", "py38"]


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
