import os
from os.path import abspath, dirname

import pytest

RELEASE_TRANSPILER_FILE_PATH = abspath(
    dirname(dirname(abspath(__file__))) + "/komodo/release_transpiler.py"
)
VALID_RELEASE_FOLDER = abspath(dirname(__file__) + "/data/test_releases")
VALID_RELEASE_BASE = "2020.01.a1"
VALID_OVERRIDE_MAPPING_FILE = abspath(
    dirname(dirname(__file__)) + "/examples/stable.yml"
)  # "/Users/JONAK/Documents/FMU/SCOUT/komodo/examples/stable.yml"
VALID_PYTHON_COORDS = "3.6,3.8"


# TESTING COMBINER
@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8,3.6",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords py3.8",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords test",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8, 3.6",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords true",
            512,
        ),
    ],
)
def test_combine_py_coords_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} combine {args}")
    assert exit_code == expectedExitCode


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8,3.6",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            0,
        ),
        (
            f"--release-folder FOLDER/DOES/NOT/EXIST --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            512,
        ),
        (
            f"--release-folder true --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            512,
        ),
        (
            f"--release-folder null --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            512,
        ),
        (
            f"--release-folder random --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            512,
        ),
    ],
)
def test_combine_py_release_folder_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} combine {args}")
    assert exit_code == expectedExitCode


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8,3.6",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE}",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping FAKE/PATH/mapping.yml",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping fake_mapping.yml",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping random_string",
            512,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping 0",
            512,
        ),
    ],
)
def test_combine_py_override_mapping_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} combine {args}")
    assert exit_code == expectedExitCode


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base {VALID_RELEASE_BASE} --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8,3.6",
            0,
        ),
        (
            f"--release-folder {VALID_RELEASE_FOLDER} --release-base INVALID_RELEASE_BASE --override-mapping {VALID_OVERRIDE_MAPPING_FILE} --py_coords 3.8,3.6",
            256,
        ),
    ],
)
def test_combine_py_release_base_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} combine {args}")
    assert exit_code == expectedExitCode


# TESTING TRANSPILER
VALID_MATRIX_FILE = abspath(dirname(__file__) + "/data/test_release_matrix.yml")
VALID_OUTPUT_FOLDER = abspath(dirname(__file__))
VALID_MATRIX_COORDINATES = "{rhel: ['7'], py: ['3.8']}"


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates '{VALID_MATRIX_COORDINATES}'",
            0,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER}",
            0,
        ),
        (
            f"--matrix-file {dirname(VALID_MATRIX_FILE)} --output-folder {VALID_RELEASE_FOLDER}",
            512,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE}/does_not_exist.yaml --output-folder {VALID_RELEASE_FOLDER}",
            512,
        ),
        (f"--matrix-file random_string --output-folder {VALID_RELEASE_FOLDER}", 512),
        (f"--matrix-file null --output-folder {VALID_RELEASE_FOLDER}", 512),
    ],
)
def test_transpile_py_matrix_file_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} transpile {args}")
    assert exit_code == expectedExitCode


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates '{VALID_MATRIX_COORDINATES}'",
            0,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER}",
            0,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER}/does_not_exist",
            512,
        ),
        (f"--matrix-file {VALID_MATRIX_FILE} --output-folder random_string", 512),
        (f"--matrix-file {VALID_MATRIX_FILE} --output-folder null", 512),
        (f"--matrix-file {VALID_MATRIX_FILE} --output-folder 0", 512),
    ],
)
def test_transpile_py_output_folder_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} transpile {args}")
    assert exit_code == expectedExitCode


@pytest.mark.parametrize(
    "args, expectedExitCode",
    [
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates '{VALID_MATRIX_COORDINATES}'",
            0,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER}",
            0,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates 0",
            256,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates random_string",
            256,
        ),
        (
            f"--matrix-file {VALID_MATRIX_FILE} --output-folder {VALID_RELEASE_FOLDER} --matrix-coordinates false",
            256,
        ),
    ],
)
def test_transpile_py_matrix_coordinates_type(args, expectedExitCode):
    exit_code = os.system(f"{RELEASE_TRANSPILER_FILE_PATH} transpile {args}")
    assert exit_code == expectedExitCode
