import pytest

from komodo.build import make


def test_make_with_empty_pkgs(captured_shell_commands, tmpdir):
    make({}, {}, {}, str(tmpdir))
    assert len(captured_shell_commands) == 1
    assert "mkdir" in " ".join(captured_shell_commands[0])


@pytest.mark.usefixtures("captured_shell_commands")
def test_make_sh_does_not_accept_pypi_package_name(tmpdir):
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
        make(packages, repositories, {}, str(tmpdir))
