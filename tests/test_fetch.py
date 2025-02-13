import os
from unittest.mock import patch

import pytest

from komodo.fetch import fetch


def test_make_one_pip_package(captured_shell_commands, tmpdir):
    packages = {"pyaml": "20.4.0"}
    repositories = {
        "pyaml": {
            "20.4.0": {
                "source": "pypi",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            },
        },
    }

    fetch(packages, repositories, str(tmpdir))

    assert len(captured_shell_commands) == 1

    command = " ".join(captured_shell_commands[0])

    assert command.startswith("pip download")
    assert "pyaml" in command


def test_version_plus_marker(captured_shell_commands, tmpdir):
    packages = {"ert": "2.25.0+py10"}
    repositories = {
        "ert": {
            "2.25.0+py10": {
                "source": "pypi",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            },
        },
    }
    fetch(packages, repositories, str(tmpdir))
    assert len(captured_shell_commands) == 1

    command = " ".join(captured_shell_commands[0])
    assert command.startswith("pip download")
    assert "ert==2.25.0" in command


def test_allow_pre_release_with_dash(captured_shell_commands, tmpdir):
    packages = {"ert": "2.25.0-rc1"}
    repositories = {
        "ert": {
            "2.25.0-rc1": {
                "source": "pypi",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            },
        },
    }

    fetch(packages, repositories, str(tmpdir))

    assert len(captured_shell_commands) == 1

    command = " ".join(captured_shell_commands[0])

    assert command.startswith("pip download")
    assert "ert==2.25.0-rc1" in command


def test_fetch_with_empty_pypi_package_name(captured_shell_commands, tmpdir):
    packages = {"yaml": "20.4.0"}
    repositories = {
        "yaml": {
            "20.4.0": {
                "source": "pypi",
                "pypi_package_name": "PyYaml",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            },
        },
    }
    fetch(packages, repositories, str(tmpdir))

    assert len(captured_shell_commands) == 1

    command = " ".join(captured_shell_commands[0])

    assert command.startswith("pip download")
    assert "PyYaml" in command


@pytest.mark.usefixtures("captured_shell_commands")
def test_fetch_git_does_not_accept_pypi_package_name(tmpdir):
    packages = {"ert": "2.16.0"}
    repositories = {
        "ert": {
            "2.16.0": {
                "source": "git://github.com/equinor/ert.git",
                "pypi_package_name": "some-other-name",
                "fetch": "git",
                "make": "sh",
                "maintainer": "someone",
                "depends": [],
            },
        },
    }

    with pytest.raises(ValueError, match=r"pypi_package_name"):
        fetch(packages, repositories, str(tmpdir))


def test_fetch_git_hash(captured_shell_commands, tmpdir):
    packages = {"ert": "main"}
    repositories = {
        "ert": {
            "main": {
                "source": "git://github.com/equinor/ert.git",
                "fetch": "git",
                "make": "sh",
                "maintainer": "someone",
                "makefile": "setup-py.sh",
                "depends": [],
            },
        },
    }

    with patch("komodo.fetch.get_git_revision_hash") as mock_get_git_revision_hash:
        mock_get_git_revision_hash.return_value = (
            "439368d5f2e2eb0c0209e1b43afe6e88d58327d3"
        )
        git_hashes = fetch(packages, repositories, str(tmpdir))
        assert (
            captured_shell_commands[0]
            == "git clone -b main --quiet --recurse-submodules -- "
            "git://github.com/equinor/ert.git ert-main"
        )
        assert git_hashes == {"ert": "439368d5f2e2eb0c0209e1b43afe6e88d58327d3"}


@patch.dict(os.environ, {"ACCESS_TOKEN": "VERYSECRETTOKEN"})
def test_expand_jinja2_templates_in_source(captured_shell_commands, tmpdir):
    packages = {"secrettool": "10.0"}
    repositories = {
        "secrettool": {
            "10.0": {
                "source": "https://{{ACCESS_TOKEN}}@github.com/equinor/secrettool.git",
                "fetch": "git",
                "make": "pip",
                "maintainer": "Prop Rietary",
                "depends": [],
            },
        },
    }

    with patch("komodo.fetch.get_git_revision_hash") as mock_get_git_revision_hash:
        mock_get_git_revision_hash.return_value = ""
        fetch(packages, repositories, str(tmpdir))
        assert captured_shell_commands[0].startswith("git clone")
        assert "https://VERYSECRETTOKEN@github.com" in captured_shell_commands[0]
