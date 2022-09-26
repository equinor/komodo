import pytest

from komodo import lint_package_status

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
}


def test_missing_status():
    missing_status = {
        "package_a": {"visibility": "private"},
        "package_b": {"visibility": "private"},
    }
    with pytest.raises(SystemExit) as exit_info:
        lint_package_status.run(missing_status, REPO)
    assert str(exit_info.value) == (
        "The following packages are specified in the repository file, "
        "but not in the package status file: ['package_c']"
    )


def test_missing_repo():
    missing_status = {
        "package_a": {"visibility": "private"},
        "package_b": {"visibility": "private"},
        "package_c": {"visibility": "private"},
    }
    repo_missing = REPO.copy()
    del repo_missing["package_c"]
    with pytest.raises(SystemExit) as exit_info:
        lint_package_status.run(missing_status, repo_missing)
    assert str(exit_info.value) == (
        "The following packages are specified in the package status file, "
        "but not in the repository file: ['package_c']"
    )


def test_all_private():
    all_private = {
        "package_a": {"visibility": "private"},
        "package_b": {"visibility": "private"},
        "package_c": {"visibility": "private"},
    }
    lint_package_status.run(all_private, REPO)


def test_malformed_visibility():
    malformed_visibility = {
        "package_a": {"visibility": "privat3"},
        "package_b": {"visibility": "publ1c"},
        "package_c": dict(),
    }
    with pytest.raises(SystemExit) as exit_info:
        lint_package_status.run(malformed_visibility, REPO)

    assert "package_a: Malformed visibility: privat3" in str(exit_info.value)
    assert "package_b: Malformed visibility: publ1c" in str(exit_info.value)
    assert "package_c: Malformed visibility: None" in str(exit_info.value)


def test_malformed_maturity_and_importance():
    malformed_visibility = {
        "package_a": {"visibility": "private"},
        "package_b": {
            "visibility": "public",
            "maturity": "stabl3",
            "importance": "low",
        },
        "package_c": {
            "visibility": "public",
            "maturity": "experim3ntal",
            "importance": "h1gh",
        },
    }
    with pytest.raises(SystemExit) as exit_info:
        lint_package_status.run(malformed_visibility, REPO)

    assert "package_b: Malformed maturity: stabl3" in str(exit_info.value)
    assert "package_c: Malformed maturity: experim3ntal" in str(exit_info.value)
    assert "package_c: Malformed importance: h1gh" in str(exit_info.value)
