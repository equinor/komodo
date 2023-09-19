from pathlib import Path

import pytest

from komodo.show_version import (
    get_komodo_path,
    get_komodoenv_path,
    get_release,
    get_version,
    parse_args,
    read_config,
)


def test_read_config_file(mock_config_file):
    """Test the function that reads sectionless INI files."""
    config = read_config("foo.cfg")
    mock_config_file.assert_called_once_with("foo.cfg", "rt", encoding="utf-8")
    assert config["home"] == "/foo/bar/komodo-release-0.0.1/root/bin"


def test_get_release(mock_komodo_env_vars):
    """Check the environment variable is picked up."""
    assert get_release() == "komodo-release-0.0.1"


def test_get_release_fails_without_env_var():
    """
    Check that the script exists gracefully if not run in a komodo environment.
    """
    with pytest.raises(SystemExit) as exception_info:
        _ = get_release()
    assert "No active komodo environment found." in str(exception_info.value)


def test_get_komodo_path(mock_komodo_env_vars):
    """
    This is the standard scenario when using an ordinary komodo (not komodoenv)
    environment. This test checks that the correct path is detected from the
    mocked environment.
    """
    release = get_release()
    path = Path("/foo/bar/komodo-release-0.0.1")
    assert get_komodo_path(release) == path


def test_get_komodoenv_path(mock_komodoenv_env_vars, mock_config_file):
    """
    Komodoenv environments wrap komodo environments and hide the location of
    the manifest file. Test that the `get_komodoenv_path()` function recovers
    the actual manifest file path from the `pyvenv.cfg` file.
    """
    release = get_release()
    path = Path("/foo/bar/komodo-release-0.0.1")
    assert get_komodoenv_path(release) == path
    fname = Path("/quux/komodo-release/root/pyvenv.cfg")
    mock_config_file.assert_called_once_with(fname, "rt", encoding="utf-8")


def test_get_version(mock_komodo_env_vars, mock_version_manifest):
    """
    This test should pick up the $KOMODO_RELEASE then correctly
    read the mocked release 'manifest' file.
    """
    fname = Path("/foo/bar/komodo-release-0.0.1/komodo-release-0.0.1")
    assert get_version("foo") == "1.2.3"
    mock_version_manifest.assert_called_once_with(fname, "rt", encoding="utf-8")


def test_get_version_with_filepath(mock_version_manifest):
    """
    Passing in manifest file explicitly. Ignores the environment and handles
    the file directly.

    Note that the file loading _and validation_ is handled by
    komodo.yaml_file_types.ManifestFile, hence the different args for `open()`.
    """
    fname = "/foo/bar/komodo-release-0.0.1-py38/komodo-release-0.0.1-py38"
    args = parse_args(["foo", "--manifest-file", fname])
    assert get_version(args.package, manifest=args.manifest_file) == "1.2.3"

    # Goes through argparse.FileType via komodo.yaml_file_types.ManifestFile.
    mock_version_manifest.assert_called_once_with(fname, "r", -1, None, None)


def test_get_version_fails_with_release_file(mock_release_file):
    """
    Passing in manifest file explicitly, but the user provides a release file,
    not a 'manifest' file. (They _should_ match, but release files are written
    by users and given to kmd to contruct an environment, whereas manifest files
    are produced by kmd during environment consutruction.)
    """
    fname = "/foo/bar/releases/komodo-release-0.0.1.yml"
    with pytest.raises(AssertionError) as exception_info:
        _ = parse_args(["foo", "--manifest-file", fname])
    assert "does not appear to be a manifest file" in str(exception_info.value)

    # Goes through argparse.FileType via komodo.yaml_file_types.ManifestFile.
    mock_release_file.assert_called_once_with(fname, "r", -1, None, None)


def test_package_not_found_error(mock_komodo_env_vars, mock_version_manifest):
    """
    Detecting the environment automatically, but the requested package is not
    present in the manifest file.
    """
    args = parse_args(["quux"])
    with pytest.raises(KeyError) as exception_info:
        _ = get_version(args.package, manifest=args.manifest_file)
    message = (
        "The package quux is not found in the manifest file "
        "/foo/bar/komodo-release-0.0.1/komodo-release-0.0.1."
    )
    assert message in str(exception_info.value)


def test_package_not_found_error_using_manifest(mock_version_manifest):
    """
    Passing in a manifest file explicitly, but this time the requested package
    is not present in that file. In this case, get_vesion() doesn't know and
    can't show the path that was passed in, but the user knows it anyway.
    """
    fname = "/foo/bar/komodo-release-0.0.1/komodo-release-0.0.1"
    args = parse_args(["quux", "--manifest-file", fname])
    with pytest.raises(KeyError) as exception_info:
        _ = get_version(args.package, manifest=args.manifest_file)
    message = "The package quux is not found in the manifest file"
    assert message in str(exception_info.value)


def test_get_komodo_path_fails(mock_bad_komodo_env_vars):
    """
    If the environment has inconsistent information, or the release name
    does not match the path, then get_komodo_path cannot discover the path
    to the 'manifest' file and an exception is raised.

    For example, this test mocks an environment where KOMODO_RELEASE
    does not match anything in the PATH.
    """
    release = get_release()
    assert release == "komodo-release-0.0.1"
    with pytest.raises(RuntimeError) as exception_info:
        _ = get_komodo_path(release)
    message = "Could not retrieve the path to the release"
    assert message in str(exception_info.value)
