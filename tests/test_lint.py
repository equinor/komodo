import pytest

from komodo import lint

REPO = {
    "python": {
        "v3.14": {
            "maintainer": "ertomatic@equinor.com",
            "make": "sh",
            "makefile": "configure",
            "source": "git://github.com/python/cpython.git",
        }
    },
    "requests": {
        "8.18.4": {
            "depends": ["python"],
            "maintainer": "maintainer@equinor.com",
            "make": "pip",
            "source": "pypi",
        }
    },
    "secrettool": {
        "10.0": {
            "source": "https://{{ACCESS_TOKEN}}@github.com/equinor/secrettool.git",
            "fetch": "git",
            "make": "pip",
            "maintainer": "Prop Rietary",
        }
    },
}

RELEASE = {
    "python": "v3.14",
    "requests": "8.18.4",
}


def test_lint():
    lint_report = lint.lint(RELEASE, REPO)
    assert [] == lint_report.dependencies
    assert [] == lint_report.versions


@pytest.mark.parametrize(
    "valid",
    (
        "bleeding-py36.yml",
        "/home/anyuser/komodo/2020.01.03-py36-rhel6.yml",
        "myrelease-py36.yml",
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
        "bleeding-py36",
        "bleeding-rhel6.yml",
    ),
)
def test_release_name_invalid(invalid):
    assert lint.lint_release_name(invalid) != []
