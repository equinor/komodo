import os
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from komodo import cli
from komodo.cli import cli_main
from tests import _get_test_root


@pytest.mark.parametrize(
    "args",
    [
        (
            "--download",
            "--build",
            "--install",
            "--prefix",
            "prefix",
            "--cache",
            "cache",
            "--tmp",
            "tmp",
            "--release",
            "nominal_release",
            "--pip",
            "/usr/bin/true",
            os.path.join(_get_test_root(), "data/cli/nominal_release.yml"),
            os.path.join(_get_test_root(), "data/cli/nominal_repository.yml"),
            "--extra-data-dirs",
            os.path.join(_get_test_root(), "data/cli"),
            os.path.join(_get_test_root(), "data/cli/hackres"),
            os.path.join(_get_test_root(), "data/cli/hackgit"),
        ),
    ],
)
def test_main(args, tmpdir):
    tmpdir = str(tmpdir)
    shutil.copytree(
        os.path.join(_get_test_root(), "data/cli/hackres"),
        os.path.join(tmpdir, "hackres"),
    )
    shutil.copytree(
        os.path.join(_get_test_root(), "data/cli/hackgit"),
        os.path.join(tmpdir, "hackgit"),
    )

    sys.argv = [
        "kmd",
        "--workspace",
        tmpdir,
    ]
    sys.argv.extend(list(args))

    cli_main()

    release_name = args[10]
    release_path = os.path.join(tmpdir, "prefix", release_name)

    assert os.path.exists(os.path.join(release_path, "root/lib/hackres.so"))
    assert os.path.exists(os.path.join(release_path, "root/lib/python4.2.so"))
    assert os.path.exists(os.path.join(release_path, "root/bin/python4.2"))
    assert os.path.exists(os.path.join(release_path, "enable"))
    assert os.path.exists(os.path.join(release_path, "enable.csh"))

    fname = "root/bin/some-github-binary-artifact"
    downloaded_file = os.path.join(release_path, fname)
    assert os.path.exists(downloaded_file)
    assert os.access(downloaded_file, os.X_OK)

    with open(os.path.join(release_path, release_name), encoding="utf-8") as releasedoc:
        releasedoc_content = releasedoc.read()

        # ensure the alias is used when resolving the version
        assert "version: null" not in releasedoc_content

        # Ensure that the commit hash is reported as version and not the
        # branch "test-hack" specified in nominal_repository.yml
        assert "test-hash" not in releasedoc_content
        assert "version: 7f4405928bd16de496522d9301c377c7bcca5ef0" in releasedoc_content


@pytest.mark.parametrize(
    "args",
    [
        (
            os.path.join(_get_test_root(), "data/cli/minimal_release.yml"),
            os.path.join(_get_test_root(), "data/cli/minimal_repository.yml"),
            "--prefix",
            "prefix",
            "--release",
            "minimal_release",
            "--extra-data-dirs",  # Required to find test_python_builtin.sh.
            os.path.join(_get_test_root(), "data/cli"),
        ),
    ],
)
def test_minimal_main(args, tmpdir):
    """Check that a minimal example, more like that from the README, also works.

    Without --locations-config, this should not produce the scripts local & local.csh.
    """
    tmpdir = str(tmpdir)

    sys.argv = [
        "kmd",
        "--workspace",
        tmpdir,
    ]

    sys.argv.extend(list(args))

    cli_main()

    release_name = args[5]
    release_path = os.path.join(tmpdir, "prefix", release_name)

    assert os.path.exists(os.path.join(release_path, "enable"))
    assert os.path.exists(os.path.join(release_path, "enable.csh"))
    assert not os.path.exists(os.path.join(release_path, "local"))
    assert not os.path.exists(os.path.join(release_path, "local.csh"))


def test_no_overwrite_by_default(tmpdir):
    sys.argv = [
        "kmd",
        "--workspace",
        str(tmpdir),
        os.path.join(_get_test_root(), "data/cli/minimal_release.yml"),
        os.path.join(_get_test_root(), "data/cli/minimal_repository.yml"),
        "--prefix",
        "prefix",
        "--release",
        "existing_release",
        "--extra-data-dirs",  # Required to find test_python_builtin.sh.
        os.path.join(_get_test_root(), "data/cli"),
    ]
    cli_main()
    with pytest.raises(
        RuntimeError, match="Downloading to non-empty directory downloads"
    ):
        cli_main()

    # Try another rerun after we have removed the downloads and remainder from
    # failed build above:
    shutil.rmtree(tmpdir / "downloads")
    shutil.rmtree(tmpdir / ".existing_release")
    with pytest.raises(RuntimeError, match="Only bleeding builds can be overwritten"):
        cli_main()


def test_bleeding_overwrite_by_default(tmpdir):
    sys.argv = [
        "kmd",
        "--workspace",
        str(tmpdir),
        os.path.join(_get_test_root(), "data/cli/minimal_release.yml"),
        os.path.join(_get_test_root(), "data/cli/minimal_repository.yml"),
        "--prefix",
        "prefix",
        "--release",
        "some_bleeding_release",
        "--extra-data-dirs",  # Required to find test_python_builtin.sh.
        os.path.join(_get_test_root(), "data/cli"),
    ]
    cli_main()
    # Remove non-interesting leftovers from first build:
    shutil.rmtree(tmpdir / "downloads")
    shutil.rmtree(tmpdir / ".some_bleeding_release")

    # Assert that we can overwrite the build inside "some_bleeding_release"
    cli_main()


def test_overwrite_if_option_is_set(tmpdir):
    sys.argv = [
        "kmd",
        "--workspace",
        str(tmpdir),
        "--overwrite",
        os.path.join(_get_test_root(), "data/cli/minimal_release.yml"),
        os.path.join(_get_test_root(), "data/cli/minimal_repository.yml"),
        "--prefix",
        "prefix",
        "--release",
        "some_release",
        "--extra-data-dirs",  # Required to find test_python_builtin.sh.
        os.path.join(_get_test_root(), "data/cli"),
    ]
    cli_main()
    # Remove non-interesting leftovers from first build:
    shutil.rmtree(tmpdir / "downloads")
    shutil.rmtree(tmpdir / ".some_release")

    # Assert that we can overwrite the build inside "some_release"
    cli_main()


def test_bleeding_builds_marked_for_deletion_are_removed(tmpdir):
    prefix_path = Path(tmpdir).absolute()
    prefix_path_str = str(prefix_path)

    sys.argv = [
        "kmd",
        "--workspace",
        str(tmpdir),
        os.path.join(_get_test_root(), "data/cli/minimal_release.yml"),
        os.path.join(_get_test_root(), "data/cli/minimal_repository.yml"),
        "--prefix",
        prefix_path_str,
        "--release",
        "some_bleeding_release",
        "--extra-data-dirs",  # Required to find test_python_builtin.sh.
        os.path.join(_get_test_root(), "data/cli"),
    ]

    test_dirs = [
        prefix_path_str + "/some_bleeding_release.delete-7632",
        prefix_path_str + "/some_bleeding_release.delete-4342",
        prefix_path_str + "/some_bleeding_release.delete-1234",
    ]

    def count_release_folders_to_be_deleted() -> int:
        release_dir_glob = [
            str(p.absolute())
            for p in list(Path(prefix_path).glob("some_bleeding_release.delete-*"))
        ]
        return len(release_dir_glob) if release_dir_glob else 0

    for test_dir in test_dirs:
        os.makedirs(test_dir)

    assert count_release_folders_to_be_deleted() == len(test_dirs)
    cli_main()
    assert count_release_folders_to_be_deleted() == 0


def test_komodo_shims_is_installed_at_the_end(tmpdir):
    (Path(tmpdir) / "release.yml").write_text(
        "komodo-shims: 1.0.0\npython: 3-builtin\ntreelib: 1.7.0", encoding="utf-8"
    )
    repo = {
        "python": {
            "3-builtin": {
                "make": "pip",  # because why not
                "maintainer": "foo",
            }
        },
        "treelib": {
            "1.7.0": {
                "source": "pypi",
                "make": "pip",
                "maintainer": "bar",
                "depends": ["python"],
            }
        },
        "komodo-shims": {
            "1.0.0": {"source": "pypi", "make": "pip", "maintainer": "com"}
        },
    }
    (Path(tmpdir) / "repository.yml").write_text(yaml.dump(repo), encoding="utf-8")
    sys.argv = [
        "kmd",
        "--workspace",
        str(tmpdir),
        str(tmpdir / "release.yml"),
        str(tmpdir / "repository.yml"),
        "--release",
        "a_komodo_release_with_shims",
        "--prefix",
        str(tmpdir),
    ]

    mocked_shell = Mock(return_value=b"")
    mocked_fetch = Mock(return_value={})
    with patch.object(cli, "shell", mocked_shell), patch.object(
        cli, "fetch", mocked_fetch
    ):
        cli_main()
    pip_install_calls = [
        shell_call
        for shell_call in mocked_shell.mock_calls
        if "'pip', 'install " in str(shell_call.args[0])
    ]
    assert len(pip_install_calls) == 3
    assert "komodo-shims" in str(pip_install_calls[-1])
