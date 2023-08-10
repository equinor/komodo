import argparse
import sys
from contextlib import contextmanager
from os.path import abspath, dirname
from typing import List

import pytest

from komodo.release_transpiler import main as release_transpiler_main

VALID_RELEASE_FOLDER = abspath(dirname(__file__) + "/data/test_releases")
VALID_RELEASE_BASE = "2020.01.a1"
VALID_OVERRIDE_MAPPING_FILE = abspath(
    dirname(dirname(__file__)) + "/examples/stable.yml"
)
VALID_PYTHON_COORDS = "3.6,3.8"
VALID_MATRIX_FILE = abspath(dirname(__file__) + "/data/test_release_matrix.yml")
VALID_OUTPUT_FOLDER = abspath(dirname(__file__))
VALID_MATRIX_COORDINATES = "{rhel: ['7'], py: ['3.8']}"


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "py3.8",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "test",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "'3.8, 3.6'",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "4.2",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "true",
            ],
            pytest.raises(SystemExit),
        ),
    ],
)
def test_combine_py_coords_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                "FOLDER/DOES/NOT/EXIST",
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "combine",
                "--release-folder",
                "true",
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "combine",
                "--release-folder",
                "null",
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "combine",
                "--release-folder",
                "random",
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            pytest.raises(NotADirectoryError),
        ),
    ],
)
def test_combine_py_release_folder_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                "FAKE/PATH/mapping.yml",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                "fake_mapping.yml",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                "random",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                "0",
            ],
            pytest.raises(FileNotFoundError),
        ),
    ],
)
def test_combine_py_override_mapping_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                VALID_RELEASE_BASE,
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "combine",
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--release-base",
                "INVALID_RELEASE_BASE",
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            pytest.raises(argparse.ArgumentTypeError),
        ),
    ],
)
def test_combine_py_release_base_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                dirname(VALID_MATRIX_FILE),
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                f"{VALID_MATRIX_FILE}/does_not_exist.yml",
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                "random_string",
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                "null",
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            pytest.raises(FileNotFoundError),
        ),
    ],
)
def test_transpile_py_matrix_file_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                f"{VALID_RELEASE_FOLDER}/does_not_exist",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                "random_string",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                "null",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                "0",
            ],
            pytest.raises(NotADirectoryError),
        ),
    ],
)
def test_transpile_py_output_folder_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    "args, expectation",
    [
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            does_not_raise(),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                "0",
            ],
            pytest.raises(TypeError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                "random_string",
            ],
            pytest.raises(TypeError),
        ),
        (
            [
                "transpile",
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                "false",
            ],
            pytest.raises(TypeError),
        ),
    ],
)
def test_transpile_py_matrix_coordinates_type(
    args: List[str], expectation, monkeypatch
):
    monkeypatch.setattr(sys, "argv", [""] + args)
    with expectation:
        release_transpiler_main()
