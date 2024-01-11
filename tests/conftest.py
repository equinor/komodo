import os
from unittest.mock import mock_open, patch

import pytest


@pytest.fixture()
def mock_komodo_env_vars():
    """Provide the environment vars from a komodo environment."""
    env = {
        "PATH": "/foo/bar/komodo-release-0.0.1/root/bin",
        "KOMODO_RELEASE": "komodo-release-0.0.1",
    }
    with patch.dict(os.environ, env):
        yield


@pytest.fixture()
def mock_bad_komodo_env_vars():
    """Provide environment vars from a komodo environment, but the variables are
    not consistent with each other.
    """
    env = {
        "PATH": "/foo/bar/komodo-release-99.99.99/root/bin",
        "KOMODO_RELEASE": "komodo-release-0.0.1",
    }
    with patch.dict(os.environ, env):
        yield


@pytest.fixture()
def mock_komodoenv_env_vars():
    """Provide the environment vars for a *komodoenv* environment. These are
    different from komodo environments in that the name will not necessarily
    match an original komodo release, and the given path does not contain a
    komodo manifest file.
    """
    env = {
        "PATH": "/quux/komodo-release/root/bin",
        "KOMODO_RELEASE": "/quux/komodo-release",
    }
    with patch.dict(os.environ, env):
        yield


@pytest.fixture()
def mock_config_file():
    """Mock a sectionless INI file, which is the format komodoenv writes into
    the pyvenv.cfg file that points to the real komodo root.
    """
    read_data = (
        "home = /foo/bar/komodo-release-0.0.1/root/bin\n"
        "include-system-site-packages = false\n"
        "version = 3.8.14\n"
    )
    m = mock_open(read_data=read_data)
    with patch("builtins.open", m):
        yield m


@pytest.fixture()
def mock_version_manifest():
    """Mock the manifest file that komodo creates when building an environment."""
    read_data = (
        "foo:\n  maintainer: jdoe\n  version: 1.2.3\n"
        "bar:\n  maintainer: jbloggs\n  version: 99.99.99"
    )
    m = mock_open(read_data=read_data)
    with patch("builtins.open", m):
        yield m


@pytest.fixture()
def mock_release_file():
    """Mock a release specification file that komodo _consumes_ when building
    an environment. Passing it to komodo-show-version raises an error.
    """
    read_data = "foo: 1.2.3\nbar: 99.99.99"
    m = mock_open(read_data=read_data)
    with patch("builtins.open", m):
        yield m


@pytest.fixture()
def captured_shell_commands(monkeypatch):
    commands = []
    with monkeypatch.context() as m:
        m.setattr("komodo.build.shell", lambda cmd: commands.append(cmd))
        m.setattr("komodo.fetch.shell", lambda cmd: commands.append(cmd))
        yield commands
