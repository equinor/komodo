import sys
from contextlib import contextmanager
from os.path import abspath, dirname

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
def test_transpile_py_matrix_file_type(args: list[str], expectation, monkeypatch):
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
def test_transpile_py_output_folder_type(args: list[str], expectation, monkeypatch):
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
    args: list[str],
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
