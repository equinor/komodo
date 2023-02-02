import os

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

expected_result = """lib1:
  1.2.3:
    source: pypi
  0.1.2:
    source: pypi

lib2:
  2.3.4:
    depends:
      - lib1
  1.2.3:
    depends:
      - lib1

lib3:
  3.4.5:
    depends:
      - lib1
  2.3.4:
    depends:
      - lib1

lib4: # comment to be preserved
  3.4.5:
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

    assert set(used_versions["lib1"]) == set(["1.2.3", "0.1.2"])
    assert set(used_versions["lib2"]) == set(["2.3.4", "1.2.3"])
    assert set(used_versions["lib3"]) == set(["3.4.5", "2.3.4"])
    assert set(used_versions["lib4"]) == set(["3.4.5"])


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
            os.path.join(_get_test_root(), "data/test_repository.yml")
        )
        unused_versions = find_unused_versions(used_versions, repository)
        remove_unused_versions(repository, unused_versions)
        write_to_file(repository, "output_repo.yml")
        with open("output_repo.yml") as output:
            assert output.read() == expected_result


def test_cleanup_argparse(tmpdir):
    with pytest.raises(SystemExit):
        main(
            [
                "--repository",
                "nonexisting_file.yml",
                "--releases",
                "non_exisiting_path",
                "--check",
            ]
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
            ]
        )

    main(
        [
            "cleanup",
            "--repository",
            os.path.realpath(
                os.path.join(_get_test_root(), "data/test_repository.yml")
            ),
            "--releases",
            os.path.join(_get_test_root(), "data/test_releases"),
            "--check",
        ]
    )

    with pytest.raises(SystemExit):
        main(
            [
                "cleanup",
                "--repository",
                "--check",
                "--stdout",
                os.path.realpath(
                    os.path.join(_get_test_root(), "data/test_repository.yml")
                ),
                "--releases",
                os.path.join(_get_test_root(), "data/test_releases"),
            ]
        )

    with tmpdir.as_cwd():
        main(
            [
                "cleanup",
                "--repository",
                os.path.realpath(
                    os.path.join(_get_test_root(), "data/test_repository.yml")
                ),
                "--releases",
                os.path.join(_get_test_root(), "data/test_releases"),
                "--output",
                "output_repo.yml",
            ]
        )
        assert os.path.isfile("output_repo.yml")
