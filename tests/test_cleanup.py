import os
import sys
from contextlib import contextmanager
from typing import List

import pytest

from komodo.cleanup import main as cleanup_main


@contextmanager
def does_not_raise():
    yield


VALID_REPOSITORY_FILE_CONTENT = """
testpackage_a:
  1.2.0:
   source: pypi
   make: pip
   maintainer: scout

testpackage_b:
  0.12.0:
   source: pypi
   make: pip
   maintainer: scout
   depends:
     - testpackage_a


testpackage_c:
  0.2.0:
   source: pypi
   make: pip
   maintainer: scout
   depends:
     - testpackage_a


testpackage_d:
  4.3.21:
   source: pypi
   make: pip
   maintainer: scout
   depends:
     - testpackage_a
     - testpackage_b
     - testpackage_c

testpackage_e:
  1.10.0:
    source: pypi
    make: pip
    maintainer: scout
"""

VALID_RELEASE_FILE_CONTENT = """
testpackage_a: 1.2.0
testpackage_b: 0.12.0
testpackage_c: 0.2.0
testpackage_d: 4.3.21
testpackage_e: 1.10.0
"""


def _write_file(file_path: str, file_content: str) -> str:
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(file_content)
    return file_path


def _create_tmp_test_files(
    repository_file_content: str,
    release_files_contents: List[str],
) -> (str, List[str]):
    folder_name = os.path.join(os.getcwd(), "test_cleanup/")
    os.mkdir(folder_name)
    repository_file_path = _write_file(
        f"{folder_name}/repository.yml",
        repository_file_content,
    )
    release_files_paths = []
    for file_number, release_file_content in enumerate(release_files_contents):
        release_file_path = _write_file(
            f"{folder_name}/release_file_{file_number}.yml",
            release_file_content,
        )
        release_files_paths.append(release_file_path)
    return (repository_file_path, release_files_paths)


@pytest.mark.parametrize(
    ("repository_file_content", "release_files_content", "expected_print"),
    [
        pytest.param(
            VALID_REPOSITORY_FILE_CONTENT,
            [VALID_RELEASE_FILE_CONTENT, VALID_RELEASE_FILE_CONTENT],
            "ok",
            id="valid_input",
        ),
        pytest.param(
            VALID_REPOSITORY_FILE_CONTENT,
            ["""unknown_package: 0.0.1"""],
            "unused",
            id="repository_missing_package",
        ),
    ],
)
def test_cleanup_main(
    repository_file_content: str,
    release_files_content: List[str],
    expected_print,
    monkeypatch,
    tmpdir,
    capsys,
):
    with tmpdir.as_cwd():
        (repository_file_path, release_file_paths) = _create_tmp_test_files(
            repository_file_content,
            release_files_content,
        )

    monkeypatch.setattr(sys, "argv", ["", repository_file_path, *release_file_paths])
    cleanup_main()
    output_print = capsys.readouterr()
    assert expected_print in output_print.out


@pytest.mark.parametrize(
    ("repository_file_content", "release_files_content", "expectation"),
    [
        pytest.param(
            "test_package:\n  1.0",
            ["""test_package: 0.0.1"""],
            pytest.raises(SystemExit, match="does not appear to be a repository file"),
            id="invalid_repository_file",
        ),
        pytest.param(
            """test_package:\n  '1.0.2':\n    maintainer: scout\n    make: pip""",
            ["""TEST_package: 1.2"""],
            pytest.raises(SystemExit, match="does not appear to be a release file"),
            id="invalid_release_file",
        ),
    ],
)
def test_cleanup_main_invalid_input_files(
    repository_file_content: str,
    release_files_content: List[str],
    expectation,
    monkeypatch,
    tmpdir,
):
    with tmpdir.as_cwd():
        (repository_file_path, release_file_paths) = _create_tmp_test_files(
            repository_file_content,
            release_files_content,
        )

    monkeypatch.setattr(sys, "argv", ["", repository_file_path, *release_file_paths])
    with expectation:
        cleanup_main()
