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
    dirname(dirname(__file__)) + "/examples/stable.yml",
)
VALID_PYTHON_COORDS = "3.6,3.8"
VALID_MATRIX_FILE = abspath(dirname(__file__) + "/data/test_release_matrix.yml")
VALID_OUTPUT_FOLDER = abspath(dirname(__file__))
VALID_MATRIX_COORDINATES = "{rhel: ['7'], py: ['3.8']}"


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [],
            does_not_raise(),
        ),
        (
            [
                "--py_coords",
                "py3.8",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "--py_coords",
                "test",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "--py_coords",
                "'3.8, 3.6'",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "--py_coords",
                "4.2",
            ],
            pytest.raises(SystemExit),
        ),
        (
            [
                "--py_coords",
                "true",
            ],
            pytest.raises(SystemExit),
        ),
    ],
)
def test_combine_py_coords_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "",
            "combine",
            "--release-folder",
            VALID_RELEASE_FOLDER,
            "--release-base",
            VALID_RELEASE_BASE,
            "--override-mapping",
            VALID_OVERRIDE_MAPPING_FILE,
            *args,
        ],
    )
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--release-folder",
                VALID_RELEASE_FOLDER,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "--release-folder",
                VALID_RELEASE_FOLDER,
            ],
            does_not_raise(),
        ),
        (
            [
                "--release-folder",
                "FOLDER/DOES/NOT/EXIST",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--release-folder",
                "true",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--release-folder",
                "null",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--release-folder",
                "random",
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            pytest.raises(NotADirectoryError),
        ),
    ],
)
def test_combine_py_release_folder_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "",
            "combine",
            "--release-base",
            VALID_RELEASE_BASE,
            "--override-mapping",
            VALID_OVERRIDE_MAPPING_FILE,
            *args,
        ],
    )
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
                "--py_coords",
                "3.8,3.6",
            ],
            does_not_raise(),
        ),
        (
            [
                "--override-mapping",
                VALID_OVERRIDE_MAPPING_FILE,
            ],
            does_not_raise(),
        ),
        (
            [
                "--override-mapping",
                "FAKE/PATH/mapping.yml",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--override-mapping",
                "fake_mapping.yml",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--override-mapping",
                "random",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--override-mapping",
                "0",
            ],
            pytest.raises(FileNotFoundError),
        ),
    ],
)
def test_combine_py_override_mapping_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "",
            "combine",
            "--release-base",
            VALID_RELEASE_BASE,
            "--release-folder",
            VALID_RELEASE_FOLDER,
            *args,
        ],
    )

    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--release-base",
                VALID_RELEASE_BASE,
            ],
            does_not_raise(),
        ),
        (
            [
                "--release-base",
                "INVALID_RELEASE_BASE",
            ],
            pytest.raises(argparse.ArgumentTypeError),
        ),
    ],
)
def test_combine_py_release_base_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "",
            "combine",
            "--release-folder",
            VALID_RELEASE_FOLDER,
            "--override-mapping",
            VALID_OVERRIDE_MAPPING_FILE,
            "--py_coords",
            "3.8,3.6",
            *args,
        ],
    )
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--matrix-file",
                VALID_MATRIX_FILE,
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [
                "--matrix-file",
                VALID_MATRIX_FILE,
            ],
            does_not_raise(),
        ),
        (
            [
                "--matrix-file",
                dirname(VALID_MATRIX_FILE),
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--matrix-file",
                f"{VALID_MATRIX_FILE}/does_not_exist.yml",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--matrix-file",
                "random_string",
            ],
            pytest.raises(FileNotFoundError),
        ),
        (
            [
                "--matrix-file",
                "null",
            ],
            pytest.raises(FileNotFoundError),
        ),
    ],
)
def test_transpile_py_matrix_file_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["", "transpile", "--output-folder", VALID_RELEASE_FOLDER, *args],
    )
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--output-folder",
                VALID_RELEASE_FOLDER,
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [
                "--output-folder",
                VALID_RELEASE_FOLDER,
            ],
            does_not_raise(),
        ),
        (
            [
                "--output-folder",
                f"{VALID_RELEASE_FOLDER}/does_not_exist",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--output-folder",
                "random_string",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--output-folder",
                "null",
            ],
            pytest.raises(NotADirectoryError),
        ),
        (
            [
                "--output-folder",
                "0",
            ],
            pytest.raises(NotADirectoryError),
        ),
    ],
)
def test_transpile_py_output_folder_type(args: List[str], expectation, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["", "transpile", "--matrix-file", VALID_MATRIX_FILE, *args],
    )
    with expectation:
        release_transpiler_main()


@pytest.mark.parametrize(
    ("args", "expectation"),
    [
        (
            [
                "--matrix-coordinates",
                VALID_MATRIX_COORDINATES,
            ],
            does_not_raise(),
        ),
        (
            [],
            does_not_raise(),
        ),
        (
            [
                "--matrix-coordinates",
                "0",
            ],
            pytest.raises(TypeError),
        ),
        (
            [
                "--matrix-coordinates",
                "random_string",
            ],
            pytest.raises(TypeError),
        ),
        (
            [
                "--matrix-coordinates",
                "false",
            ],
            pytest.raises(TypeError),
        ),
    ],
)
def test_transpile_py_matrix_coordinates_type(
    args: List[str],
    expectation,
    monkeypatch,
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "",
            "transpile",
            "--matrix-file",
            VALID_MATRIX_FILE,
            "--output-folder",
            VALID_RELEASE_FOLDER,
            *args,
        ],
    )
    with expectation:
        release_transpiler_main()
