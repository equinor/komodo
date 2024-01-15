import os
from pathlib import Path

import pytest

from komodo.prettier import prettier
from komodo.release_cleanup import (
    find_unused_versions,
    load_all_releases,
    main,
    remove_unused_versions,
    write_to_file,
)
from tests import _get_test_root, _load_yaml

EXPECTED_RESULT = """lib1:
  1.2.3:
    source: pypi
    make: pip
  0.1.2:
    source: pypi
    make: pip

lib2:
  2.3.4:
    make: pip
    depends:
      - lib1
  1.2.3:
    make: pip
    depends:
      - lib1

lib3:
  3.4.5:
    make: rsync
    depends:
      - lib1
  2.3.4:
    make: rsync
    depends:
      - lib1

lib4: # comment to be preserved
  3.4.5:
    make: pip
    depends:
      - lib3
      - lib2
"""


def test_load_all_releases():
    files = [
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py27.yml"),
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py36.yml"),
    ]
    used_versions = load_all_releases(files)

    assert set(used_versions["lib1"]) == {"1.2.3", "0.1.2"}
    assert set(used_versions["lib2"]) == {"2.3.4", "1.2.3"}
    assert set(used_versions["lib3"]) == {"3.4.5", "2.3.4"}
    assert set(used_versions["lib4"]) == {"3.4.5"}


def test_unused_versions():
    files = [
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py27.yml"),
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py36.yml"),
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py38.yml"),
    ]
    used_versions = load_all_releases(files)

    repository = _load_yaml(os.path.join(_get_test_root(), "data/test_repository.yml"))
    unused_versions = find_unused_versions(used_versions, repository)
    print(prettier(repository))
    print(used_versions)
    print(unused_versions)
    assert "0.0.2" in unused_versions["lib1"]
    assert "0.0.2" in unused_versions["lib2"]
    assert "master" in unused_versions["lib3"]
    assert "lib4" not in unused_versions
    assert "1.2.3" in unused_versions["lib5"]


def test_remove_unused_versions():
    files = [
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py27.yml"),
        os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py36.yml"),
    ]
    used_versions = load_all_releases(files)
    repository = _load_yaml(os.path.join(_get_test_root(), "data/test_repository.yml"))
    unused_versions = find_unused_versions(used_versions, repository)
    remove_unused_versions(repository, unused_versions)

    assert "lib5" not in repository
    assert "0.0.2" not in repository["lib1"]
    assert "0.0.2" not in repository["lib2"]
    assert "master" not in repository["lib3"]


def test_write_to_file(tmpdir):
    with tmpdir.as_cwd():
        files = [
            os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py27.yml"),
            os.path.join(_get_test_root(), "data/test_releases/2020.01.a1-py36.yml"),
        ]
        used_versions = load_all_releases(files)
        repository = _load_yaml(
            os.path.join(_get_test_root(), "data/test_repository.yml"),
        )
        unused_versions = find_unused_versions(used_versions, repository)
        remove_unused_versions(repository, unused_versions)
        write_to_file(repository, "output_repo.yml")
        with open("output_repo.yml", encoding="utf-8") as output:
            assert output.read() == EXPECTED_RESULT


def test_return_values_of_prettier(tmpdir):
    os.chdir(tmpdir)

    # Given a yml file with extra whitespace padded at the end:
    # (a minimal change that will trigger the prettifier)
    yml_text = (Path(_get_test_root()) / "data" / "test_repository.yml").read_text(
        encoding="utf-8",
    )
    repo_with_whitespace = "repo_with_whitespace.yml"
    Path(repo_with_whitespace).write_text(yml_text + "\n", encoding="utf-8")

    # Then it will fail with exit code 1 if only checked:
    with pytest.raises(SystemExit) as exit_info:
        main(["prettier", "--check-only", "--files", repo_with_whitespace])
        assert exit_info.value.code == 1

    # Redo check to ensure the yml file was not reformatted, only checked:
    with pytest.raises(SystemExit) as exit_info:
        main(["prettier", "--check-only", "--files", repo_with_whitespace])
        assert exit_info.value.code == 1

    # If we now run without check, the file should be reformatted in-place:
    with pytest.raises(SystemExit) as exit_info:
        main(["prettier", "--files", repo_with_whitespace])
        assert exit_info.value.code == 0

    # If checked again, the file should be ok, proving it was reformatted:
    with pytest.raises(SystemExit) as exit_info:
        main(["prettier", "--check-only", "--files", repo_with_whitespace])
        assert exit_info.value.code == 0


def test_cleanup_argparse(tmpdir):
    with pytest.raises(SystemExit):
        main(
            [
                "--repository",
                "nonexisting_file.yml",
                "--releases",
                "non_exisiting_path",
                "--check",
            ],
        )

    with pytest.raises(SystemExit):
        main(
            [
                "cleanup",
                "--repository",
                os.path.join(_get_test_root(), "data/test_repository.yml"),
                "--releases",
                "non_exisiting_path",
                "--check",
            ],
        )

    main(
        [
            "cleanup",
            "--repository",
            os.path.realpath(
                os.path.join(_get_test_root(), "data/test_repository.yml"),
            ),
            "--releases",
            os.path.join(_get_test_root(), "data/test_releases"),
            "--check",
        ],
    )

    with pytest.raises(SystemExit):
        main(
            [
                "cleanup",
                "--repository",
                "--check",
                "--stdout",
                os.path.realpath(
                    os.path.join(_get_test_root(), "data/test_repository.yml"),
                ),
                "--releases",
                os.path.join(_get_test_root(), "data/test_releases"),
            ],
        )

    with tmpdir.as_cwd():
        main(
            [
                "cleanup",
                "--repository",
                os.path.realpath(
                    os.path.join(_get_test_root(), "data/test_repository.yml"),
                ),
                "--releases",
                os.path.join(_get_test_root(), "data/test_releases"),
                "--output",
                "output_repo.yml",
            ],
        )
        assert os.path.isfile("output_repo.yml")
