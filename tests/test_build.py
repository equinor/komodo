import pytest

from komodo.build import full_dfs, make


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


test_cases = [
    (
        {"dummy_package": "1.1.0"},
        {
            "dummy_package": {
                "1.1.0": {
                    "depends": [],
                },
            },
        },
        [["dummy_package"]],
    ),
    (
        {
            "package_a": "1.0.0",
            "package_b": "1.0.0",
            "package_c": "1.0.0",
            "package_d": "1.0.0",
            "package_e": "1.0.0",
        },
        {
            "package_a": {
                "1.0.0": {
                    "depends": ["package_b", "package_c"],
                },
            },
            "package_b": {
                "1.0.0": {
                    "depends": ["package_d", "package_e"],
                },
            },
            "package_c": {
                "1.0.0": {
                    "depends": ["package_d"],
                },
            },
            "package_d": {
                "1.0.0": {
                    "depends": ["package_e"],
                },
            },
            "package_e": {
                "1.0.0": {
                    "depends": [],
                },
            },
        },
        [
            ["package_e", "package_d", "package_c", "package_b", "package_a"],
            ["package_e", "package_d", "package_b", "package_c", "package_a"],
        ],
    ),
]


@pytest.mark.parametrize("packages, repositories, expected", test_cases)
def test_installation_package_order(packages, repositories, expected):
    package_order = full_dfs(packages, repositories)
    assert package_order in expected
