import pytest
from komodo import lint


REPO = {
    "python": {
        "v2.7.14": {
            "maintainer": "jokva@statoil.com",
            "make": "sh",
            "makefile": "configure",
            "source": "git://github.com/python/cpython.git",
        }
    },
    "requests": {
        "2.18.4": {
            "depends": ["python"],
            "maintainer": "jokva@statoil.com",
            "make": "pip",
            "source": "pypi",
        }
    },
}

RELEASE = {
    "python": "v2.7.14",
    "requests": "2.18.4",
}


def test_lint():
    lint_report = lint.lint(RELEASE, REPO)
    assert [] == lint_report.dependencies
    assert [] == lint_report.versions


@pytest.mark.parametrize(
    "valid",
    (
        "bleeding-py27.yml",
        "bleeding-py36.yml",
        "/home/anyuser/komodo-releases/releases/bleeding-py27.yml",
        "/home/anyuser/komodo/bleeding-py27.yml",
        "/home/anyuser/komodo/2020.01.03-py36-rhel6.yml",
        "/home/anyuser/komodo/2020.01.03-py27.yml",
        "myrelease-py27.yml",
        "myrelease-py36.yml",
        "myrelease-py27-rhel6.yml",
        "myrelease-py27-rhel7.yml",
        "myrelease-py36-rhel6.yml",
        "myrelease-py36-rhel7.yml",
    ),
)
def test_release_name_valid(valid):
    assert lint.lint_release_name(valid) == []


@pytest.mark.parametrize(
    "invalid",
    (
        "bleeding",
        "bleeding.yml",
        "2020.01.01",
        "2020.01.00.yml",
        "/home/anyuser/komodo-releases/releases/2020.01.00.yml",
        "bleeding-py27",
        "bleeding-rhel6.yml",
    ),
)
def test_release_name_invalid(invalid):
    assert lint.lint_release_name(invalid) != []
