import pytest

from komodo.check_unused_package import check_for_unused_package
from komodo.yaml_file_types import ReleaseFile, RepositoryFile

test_case = [
    (
        {
            "package_a": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                    "depends": ["package_b", "package_c"],
                },
            },
            "package_b": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                    "depends": ["package_d", "package_e"],
                },
            },
            "package_c": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                    "depends": ["package_d"],
                },
            },
            "package_d": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                    "depends": ["package_e"],
                },
            },
            "package_e": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                },
            },
            "package_f": {
                "1.0": {
                    "make": "pip",
                    "maintainer": "scout",
                    "depends": ["package_c"],
                },
            },
        },
        {
            "package_a": "1.0",
            "package_b": "1.0",
            "package_c": "1.0",
            "package_d": "1.0",
            "package_e": "1.0",
            "package_f": "1.0.0",
        },
        {
            "package_a": {
                "visibility": "public",
            },
            "package_b": {
                "visibility": "private-plugin",
            },
            "package_c": {
                "visibility": "private",
            },
            "package_d": {
                "visibility": "private",
            },
            "package_e": {
                "visibility": "private",
            },
            "package_f": {"visibility": "private"},
        },
    ),
]


@pytest.mark.parametrize("repo, release, package_status", test_case)
def test_check_unused_package(repo, release, package_status):
    package_status["python"] = {"visibility": "public"}
    release["python"] = "3.8-builtin"

    repo = RepositoryFile.from_dictionary(value=repo)
    release = ReleaseFile.from_dictionary(value=release)
    result = check_for_unused_package(
        release_file=release,
        package_status=package_status,
        repository=repo,
        builtin_python_versions={"3.8-builtin": "3.8.6"},
    )
    assert result.exitcode == 1
    assert "The following 1" in result.message and "package_f" in result.message
