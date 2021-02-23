from unittest.mock import patch

import pytest
from komodo.build import make
from komodo.package_version import LATEST_PACKAGE_ALIAS


@pytest.fixture
def captured_shell_commands(monkeypatch):
    commands = []
    with monkeypatch.context() as m:
        m.setattr("komodo.build.shell", lambda cmd: commands.append(cmd))
        yield commands


def test_make_with_empty_pkgs(captured_shell_commands, tmpdir):
    make({}, {}, {}, str(tmpdir))
    assert len(captured_shell_commands) == 1
    assert "mkdir" in " ".join(captured_shell_commands[0])


def test_make_one_pip_package(captured_shell_commands, tmpdir):
    packages = {"pyaml": "20.4.0"}
    repositories = {
        "pyaml": {
            "20.4.0": {
                "source": "pypi",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            }
        }
    }

    make(packages, repositories, {}, str(tmpdir))

    assert len(captured_shell_commands) == 2
    assert "mkdir" in " ".join(captured_shell_commands[0])
    assert "pip install pyaml" in " ".join(captured_shell_commands[1])


def test_make_one_pip_package_different_name(captured_shell_commands, tmpdir):
    packages = {"yaml": "20.4.0"}
    repositories = {
        "yaml": {
            "20.4.0": {
                "source": "pypi",
                "pypi_package_name": "PyYaml",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            }
        }
    }

    make(packages, repositories, {}, str(tmpdir))

    assert len(captured_shell_commands) == 2
    assert "mkdir" in " ".join(captured_shell_commands[0])
    assert "pip install PyYaml==20.4.0" in " ".join(captured_shell_commands[1])


def test_make_pip_package_from_latest(captured_shell_commands, tmpdir):
    packages = {"yaml": LATEST_PACKAGE_ALIAS}
    repositories = {
        "yaml": {
            LATEST_PACKAGE_ALIAS: {
                "source": "pypi",
                "pypi_package_name": "PyYaml",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            }
        }
    }

    with patch("komodo.build.latest_pypi_version") as mock_latest_version:
        mock_latest_version.return_value = "1.0.0"
        make(packages, repositories, {}, str(tmpdir))
        mock_latest_version.assert_called_once_with("PyYaml")
    assert len(captured_shell_commands) == 2
    assert "mkdir" in " ".join(captured_shell_commands[0])
    assert "pip install PyYaml==1.0.0" in " ".join(captured_shell_commands[1])


def test_make_sh_does_not_accept_pypi_package_name(captured_shell_commands, tmpdir):
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
            }
        }
    }

    with pytest.raises(ValueError, match="pypi_package_name"):
        make(packages, repositories, {}, str(tmpdir))
