import pytest

from komodo import extract_dep_graph

REPO = {
    "package_a": {
        "1.2.3": {
            "depends": ["package_b", "package_c", "package_e", "package_f"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_b": {
        "2.3.4": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
        "1.0.0": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
    },
    "package_c": {
        "0.0.1": {
            "depends": ["package_d", "package_e"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_d": {
        "10.2.1": {
            "depends": ["package_e"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_e": {"4.1.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"}},
    "package_f": {
        "0.1.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
        "1.0.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
    },
}

BASE_RELEASE = {
    "package_a": "1.2.3",
    "package_b": "2.3.4",
    "package_c": "0.0.1",
    "package_d": "10.2.1",
    "package_e": "4.1.2",
    "package_f": "1.0.2",
    "package_g": "0.5.3",
    "package_h": "1.2.7",
    "package_i": "1.2.14",
    "package_j": "1.22.3",
    "package_k": "6.2.3",
    "package_l": "3.0.2",
}

RELEASE = {
    "package_a": "1.2.3",
    "package_f": "1.0.2",
}


def test_extract_dep_graph():
    dependencies = extract_dep_graph._iterate_packages(RELEASE, BASE_RELEASE, REPO)
    assert len(dependencies.keys()) == 6
    assert "package_a" in dependencies
    assert "package_b" in dependencies
    assert "package_c" in dependencies
    assert "package_d" in dependencies
    assert "package_e" in dependencies
    assert "package_f" in dependencies
    assert dependencies["package_a"] == "1.2.3"
    assert dependencies["package_b"] == "2.3.4"
    assert dependencies["package_c"] == "0.0.1"
    assert dependencies["package_d"] == "10.2.1"
    assert dependencies["package_e"] == "4.1.2"
    assert dependencies["package_f"] == "1.0.2"


REPO_MISSING_PKG = {
    "package_a": {
        "1.2.3": {
            "depends": ["package_b"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    }
}


def test_extract_dep_graph_repo_missing_pkg():
    with pytest.raises(SystemExit) as exit_info:
        extract_dep_graph._iterate_packages(RELEASE, BASE_RELEASE, REPO_MISSING_PKG)
    assert "'package_b' not found in 'repo'. This needs to be resolved." in str(
        exit_info.value
    )


BASE_RELEASE_MISSINGS_PKGS = {
    "package_a": "1.2.3",
}


def test_extract_dep_graph_base_file_missing_pkg():
    with pytest.raises(SystemExit) as exit_info:
        extract_dep_graph._iterate_packages(RELEASE, BASE_RELEASE_MISSINGS_PKGS, REPO)
    assert (
        "'package_b' not found in 'base_pkgs'. This needs to be in place in order to pick correct version."
        in str(exit_info.value)
    )


BASE_RELEASE_DEFINES_VERSION_NOT_EXISTING = {"package_a": "1.2.3", "package_b": "2.4.3"}


def test_extract_dep_graph_base_file_faulty_version():
    with pytest.raises(SystemExit) as exit_info:
        extract_dep_graph._iterate_packages(
            RELEASE, BASE_RELEASE_DEFINES_VERSION_NOT_EXISTING, REPO
        )
    assert (
        "Version '2.4.3' for package 'package_b' not found in 'repo'. Available version(s) is: ['2.3.4', '1.0.0']."
        in str(exit_info.value)
    )


RELEASE_DEFINES_VERSION_NOT_EXISTING = {"package_a": "11.2.3"}


def test_extract_dep_graph_pkgs_file_faulty_version():
    with pytest.raises(SystemExit) as exit_info:
        extract_dep_graph._iterate_packages(
            RELEASE_DEFINES_VERSION_NOT_EXISTING, BASE_RELEASE, REPO
        )
    assert (
        "Version '11.2.3' for package 'package_a' not found in 'repo'. Available version(s) is: ['1.2.3']."
        in str(exit_info.value)
    )
