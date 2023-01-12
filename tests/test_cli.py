import os
import shutil
import sys

import pytest

from komodo.cli import cli_main
from komodo.package_version import LATEST_PACKAGE_ALIAS
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
            "/bin/true",
            "--extra-data-dirs",
            os.path.join(_get_test_root(), "data/cli"),
            os.path.join(_get_test_root(), "data/cli/hackres"),
            os.path.join(_get_test_root(), "data/cli/hackgit"),
            "--locations-config",
            os.path.join(_get_test_root(), "data/cli/locations.yml"),
            os.path.join(_get_test_root(), "data/cli/nominal_release.yml"),
            os.path.join(_get_test_root(), "data/cli/nominal_repository.yml"),
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
    assert os.path.exists(os.path.join(release_path, "local"))
    assert os.path.exists(os.path.join(release_path, "local.csh"))

    downloaded_file = os.path.join(release_path, "root/bin/some-github-binary-artifact")
    assert os.path.exists(downloaded_file)
    assert os.access(downloaded_file, os.X_OK)

    with open(os.path.join(release_path, release_name)) as releasedoc:
        releasedoc_content = releasedoc.read()

        # test specifically for the regression introduced by
        # https://github.com/equinor/komodo/issues/190 where if you provided ert
        # with version '*', it would then show up in the releasedoc.
        assert f"version: '{LATEST_PACKAGE_ALIAS}'" not in releasedoc_content

        # ensure the alias is used when resolving the version
        assert "version: null" not in releasedoc_content

        # Ensure that the commit hash is reported as version and not the
        # branch "test-hack" specified in nominal_repository.yml
        assert "test-hash" not in releasedoc_content
        assert "version: 7f4405928bd16de496522d9301c377c7bcca5ef0" in releasedoc_content
