from unittest.mock import patch

import pytest

from komodo.check_unused_package import check_for_unused_package
from komodo.pypi_dependencies import PypiDependencies
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


@pytest.fixture(autouse=True, scope="module")
def mock_get_requirements():
    with patch.object(
        PypiDependencies, "_get_requirements_from_pypi"
    ) as mock_get_requirements:
        yield
        mock_get_requirements.assert_not_called()


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
                "1.0.0": {
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
    repo["python"] = {"3.8-builtin": {"maintainer": "me", "make": "sh"}}

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


def has_unused_packages(repo, release, package_status):
    package_status["python"] = {"visibility": "public"}
    release["python"] = "3.8-builtin"
    repo["python"] = {"3.8-builtin": {"maintainer": "me", "make": "sh"}}

    return check_for_unused_package(
        release_file=ReleaseFile.from_dictionary(release),
        package_status=package_status,
        repository=RepositoryFile.from_dictionary(repo),
        builtin_python_versions={"3.8-builtin": "3.8.6"},
    )


def test_empty_release_has_no_unused_packages():
    assert has_unused_packages({}, {}, {}).exitcode == 0


def test_missing_package_status_gives_error_code_2():
    assert has_unused_packages({}, {"package": "version"}, {}).exitcode == 2


def test_missing_visibility_gives_error_code_2():
    assert (
        has_unused_packages({}, {"package": "version"}, {"package": {}}).exitcode == 2
    )


def test_missing_repo_gives_error_code_3():
    assert (
        has_unused_packages(
            {}, {"package": "version"}, {"package": {"visibility": "public"}}
        ).exitcode
        == 3
    )


def test_private_unused_package_gives_error_code_1():
    assert (
        has_unused_packages(
            {
                "package": {
                    "1.0": {"source": "github", "make": "pip", "maintainer": "me"}
                }
            },
            {"package": "1.0"},
            {"package": {"visibility": "private"}},
        ).exitcode
        == 1
    )


def test_private_unused_dependency_gives_error_code_1():
    assert (
        has_unused_packages(
            {
                "private_pkg": {
                    "1.0": {"source": "github", "make": "pip", "maintainer": "me"}
                },
                "public_pkg": {
                    "0.1": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                        "depends": ["private_pkg"],
                    }
                },
            },
            {"private_pkg": "1.0"},
            {
                "private_pkg": {"visibility": "private"},
                "public_pkg": {"visibility": "public"},
            },
        ).exitcode
        == 1
    )


@pytest.mark.parametrize("public_type", ("public", "private-plugin"))
def test_public_packages_are_used(public_type):
    assert (
        has_unused_packages(
            {
                "package": {
                    "1.0": {"source": "github", "make": "pip", "maintainer": "me"}
                }
            },
            {"package": "1.0"},
            {"package": {"visibility": public_type}},
        ).exitcode
        == 0
    )


def test_dependencies_of_public_packages_are_used():
    assert (
        has_unused_packages(
            {
                "public_package": {
                    "1.0": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                        "depends": ["private_package"],
                    }
                },
                "private_package": {
                    "0.1": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                    }
                },
            },
            {"public_package": "1.0", "private_package": "0.1"},
            {
                "public_package": {"visibility": "public"},
                "private_package": {"visibility": "private"},
            },
        ).exitcode
        == 0
    )


def test_transient_dependencies_of_public_packages_are_used():
    assert (
        has_unused_packages(
            {
                "public_package": {
                    "1.0": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                        "depends": ["private_package"],
                    }
                },
                "private_package": {
                    "0.1": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                        "depends": ["transient_package"],
                    }
                },
                "transient_package": {
                    "2.0": {
                        "source": "github",
                        "make": "pip",
                        "maintainer": "me",
                    }
                },
            },
            {
                "public_package": "1.0",
                "private_package": "0.1",
                "transient_package": "2.0",
            },
            {
                "public_package": {"visibility": "public"},
                "private_package": {"visibility": "private"},
                "transient_package": {"visibility": "private"},
            },
        ).exitcode
        == 0
    )


@pytest.mark.parametrize("public_type", ("public", "private-plugin"))
def test_public_packages_are_used_redundant_package_status_has_no_effect(public_type):
    assert (
        has_unused_packages(
            {
                "package": {
                    "1.0": {"source": "github", "make": "pip", "maintainer": "me"}
                }
            },
            {"package": "1.0"},
            {
                "package": {"visibility": public_type},
                "package1": {"visibility": public_type},
                "package2": {"visibility": "private"},
                "package3": {"visibility": "private"},
            },
        ).exitcode
        == 0
    )


def test_multiple_private_packages_unused():
    repo = {
        "public_pkg": {
            "1.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
                "depends": ["used_private_pkg"],
            }
        },
        "used_private_pkg": {
            "0.1": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
            }
        },
        "unused_private_pkg1": {
            "2.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
            }
        },
        "unused_private_pkg2": {
            "3.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
            }
        },
    }
    release = {
        "public_pkg": "1.0",
        "used_private_pkg": "0.1",
        "unused_private_pkg1": "2.0",
        "unused_private_pkg2": "3.0",
    }
    package_status = {
        "public_pkg": {"visibility": "public"},
        "used_private_pkg": {"visibility": "private"},
        "unused_private_pkg1": {"visibility": "private"},
        "unused_private_pkg2": {"visibility": "private"},
    }

    result = has_unused_packages(repo, release, package_status)

    assert result.exitcode == 1
    assert "The following 2 private packages are" in result.message
    assert "unused_private_pkg1" in result.message
    assert "unused_private_pkg2" in result.message


def test_private_package_used_by_another_private_package_reported_as_unused():
    repo = {
        "private_pkg1": {
            "1.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
                "depends": ["private_pkg2"],
            }
        },
        "private_pkg2": {
            "2.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
            }
        },
        "private_pkg3": {
            "3.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
            }
        },
    }
    release = {
        "private_pkg1": "1.0",
        "private_pkg2": "2.0",
        "private_pkg3": "3.0",
    }
    package_status = {
        "private_pkg1": {"visibility": "private"},
        "private_pkg2": {"visibility": "private"},
        "private_pkg3": {"visibility": "private"},
    }

    result = has_unused_packages(repo, release, package_status)

    assert result.exitcode == 1
    assert "The following 3 private packages are" in result.message
    assert "private_pkg1" in result.message
    assert "private_pkg2" in result.message
    assert "private_pkg3" in result.message


def test_circular_dependencies_handled_gracefully():
    repo = {
        "circular_pkg1": {
            "1.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
                "depends": ["circular_pkg2"],
            }
        },
        "circular_pkg2": {
            "2.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
                "depends": ["circular_pkg1"],
            }
        },
        "public_pkg": {
            "3.0": {
                "source": "github",
                "make": "pip",
                "maintainer": "me",
                "depends": ["circular_pkg1"],
            }
        },
    }
    release = {
        "circular_pkg1": "1.0",
        "circular_pkg2": "2.0",
        "public_pkg": "3.0",
    }
    package_status = {
        "circular_pkg1": {"visibility": "private"},
        "circular_pkg2": {"visibility": "private"},
        "public_pkg": {"visibility": "public"},
    }

    result = has_unused_packages(repo, release, package_status)

    assert result.exitcode == 0  # No unused packages should be reported
    assert "Everything seems fine." in result.message
