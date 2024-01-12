import os
import pathlib
import sys
from unittest.mock import MagicMock

import pytest
import requests
from packaging import version
from ruamel.yaml import YAML

from komodo import check_up_to_date_pypi
from komodo.check_up_to_date_pypi import (
    compatible_versions,
    get_pypi_packages,
    get_upgrade_proposals_from_pypi,
    insert_upgrade_proposals,
    run_check_up_to_date,
    yaml_parser,
)


@pytest.mark.parametrize(
    "input_dict",
    [
        pytest.param({"1.0.0": []}, id="Just valid tag"),
        pytest.param({"1.0.0": [], "2.0.0a0": []}, id="Pre-release tag"),
        pytest.param({"1.0.0": [], "2.0.0.dev": []}, id="Dev tag"),
        pytest.param(
            {"1.0.0": [], "2.0.0": [{"requires_python": ">3.7"}]},
            id="Too high python requirement on 2.0",
        ),
        pytest.param(
            {
                "1.0.0": [{"requires_python": ">3"}],
                "2.0.0": [{"requires_python": ">3.7"}],
            },
            id="Latest version not compatible",
        ),
    ],
)
def test_compatible_versions(input_dict):
    result = compatible_versions(input_dict, "3.6.10")
    assert result == [version.parse("1.0.0")]


@pytest.mark.parametrize(
    ("input_release", "input_repo"),
    [
        pytest.param(
            {"dummy_package": "1.0.0"},
            {"dummy_package": {"1.0.0": {"source": "pypi"}}},
            id="Minimum requirement",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"source": "not_pypi"}},
            },
            id="Not all pypi",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            },
            id="No source for one package",
        ),
    ],
)
def test_get_pypi_packages(input_release, input_repo):
    result = get_pypi_packages(input_release, input_repo)
    assert result == ["dummy_package"]


@pytest.mark.parametrize(
    ("release", "repository", "suggestions", "expected"),
    [
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Base line test",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Nothing to add to repository",
        ),
        pytest.param(
            {"dummy_package": "1.0.0+py23", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0+py23": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0+py23"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0+py23": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Test with +something marker on version",
        ),
    ],
)
def test_insert_upgrade_proposals(release, repository, suggestions, expected):
    yaml = yaml_parser()
    repository = yaml.load(str(repository))
    release = yaml.load(str(release))
    insert_upgrade_proposals(
        suggestions,
        repository,
        release,
    )
    assert {"release": release, "repo": repository} == expected


def test_run(monkeypatch):
    release = {"dummy_package": "1.0.0", "custom_package": "1.1.1"}
    repository = {
        "dummy_package": {"1.0.0": {"source": "pypi"}},
        "custom_package": {"1.1.1": {"maintainer": "some_person"}},
    }

    response_mock = MagicMock(return_value=[("dummy_package", MagicMock())])
    compatible_versions = MagicMock(return_value=["2.0.0"])
    monkeypatch.setattr(check_up_to_date_pypi, "get_pypi_info", response_mock)
    monkeypatch.setattr(
        check_up_to_date_pypi,
        "compatible_versions",
        compatible_versions,
    )
    result = get_upgrade_proposals_from_pypi(release, repository, "3.6.8")
    assert result == {"dummy_package": {"previous": "1.0.0", "suggested": "2.0.0"}}


def test_main_happy_path(monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        arguments = [
            "script_name",
            "release_file",
            "repository_file",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        monkeypatch.setattr(pathlib.Path, "is_file", MagicMock(return_value=True))
        monkeypatch.setattr(check_up_to_date_pypi, "load_from_file", MagicMock())
        output_mock = MagicMock(return_value={})
        monkeypatch.setattr(
            check_up_to_date_pypi,
            "get_upgrade_proposals_from_pypi",
            output_mock,
        )
        run_check_up_to_date(
            "release_file",
            "repository_file",
            propose_upgrade="new_file",
        )


def test_main_upgrade_proposal(monkeypatch, capsys):
    arguments = [
        "script_name",
        "release_file",
        "repository_file",
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    input_mock = MagicMock()
    monkeypatch.setattr(check_up_to_date_pypi, "load_from_file", input_mock)
    monkeypatch.setattr(pathlib.Path, "is_file", MagicMock(return_value=True))
    output_mock = MagicMock(
        return_value={"dummy_package": {"previous": "1.0.0", "suggested": "2.0.0"}},
    )
    monkeypatch.setattr(
        check_up_to_date_pypi,
        "get_upgrade_proposals_from_pypi",
        output_mock,
    )

    run_check_up_to_date("release_file", "repository_file")
    print_message = capsys.readouterr().out
    assert (
        "dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0" in print_message
    )


def test_check_up_to_date_file_output(monkeypatch, tmpdir, capsys):
    yaml = YAML()
    with tmpdir.as_cwd():
        base_path = os.getcwd()
        with open("release_file.yml", mode="w", encoding="utf-8") as f:
            yaml.dump({"dummy_package": "1.0.0", "custom_package": "1.1.1"}, f)
        with open("repository_file.yml", mode="w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "dummy_package": {"1.0.0": {"source": "pypi"}},
                    "custom_package": {"1.1.1": {"maintainer": "some_person"}},
                },
                f,
            )
        request_mock = MagicMock()
        request_mock.json.return_value = {
            "releases": {
                "2.2.0": [{"yanked": True}],
                "2.0.0": [{"requires_python": ">=3.8"}],
            },
        }
        monkeypatch.setattr(requests, "get", MagicMock(return_value=request_mock))

        run_check_up_to_date(
            f"{base_path}/release_file.yml",
            f"{base_path}/repository_file.yml",
            propose_upgrade=True,
        )
        print_message = capsys.readouterr().out
        assert (
            "dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0"
            in print_message
        )
        result = {}

        with open(f"{base_path}/repository_file.yml", encoding="utf-8") as fin:
            result["updated_repo"] = yaml.load(fin)

        assert result == {
            "updated_repo": {
                "dummy_package": {
                    "2.0.0": {"source": "pypi"},
                    "1.0.0": {"source": "pypi"},
                },
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            },
        }


@pytest.mark.parametrize(
    ("release", "repository", "request_json", "expected"),
    [
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {
                    "1.0.0": {"maintainer": "scout", "make": "pip", "source": "pypi"},
                },
                "custom_package": {
                    "1.1.1": {
                        "maintainer": "some_person",
                        "make": "sh",
                        "source": "https://test.com/",
                    },
                },
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                        "1.0.0": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                    },
                    "custom_package": {
                        "1.1.1": {
                            "maintainer": "some_person",
                            "make": "sh",
                            "source": "https://test.com/",
                        },
                    },
                },
            },
            id="Base line test",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "komodo_version_package": "1.*"},
            {
                "dummy_package": {
                    "1.0.0": {"maintainer": "scout", "make": "pip", "source": "pypi"},
                },
                "komodo_version_package": {
                    "1.*": {"maintainer": "scout", "make": "pip", "source": "pypi"},
                },
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {
                    "dummy_package": "2.0.0",
                    "komodo_version_package": "1.*",
                },
                "repo": {
                    "dummy_package": {
                        "2.0.0": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                        "1.0.0": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                    },
                    "komodo_version_package": {
                        "1.*": {"maintainer": "scout", "make": "pip", "source": "pypi"},
                    },
                },
            },
            id="With komodo package alias not updated",
        ),
        pytest.param(
            {"dummy_package": "1.0.0+py27"},
            {
                "dummy_package": {
                    "1.0.0+py27": {
                        "maintainer": "scout",
                        "make": "pip",
                        "source": "pypi",
                    },
                },
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                        "1.0.0+py27": {
                            "maintainer": "scout",
                            "make": "pip",
                            "source": "pypi",
                        },
                    },
                },
            },
            id="Using version suffix",
        ),
        pytest.param(
            {"dummy_package": "1.0.0"},
            {
                "dummy_package": {
                    "1.0.0": {"maintainer": "scout", "make": "pip", "source": "pypi"},
                },
            },
            {
                "releases": {"2.2.0": [{"yanked": True}], "2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "1.0.0": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                    },
                },
            },
            id="Yanked from pypi",
        ),
    ],
)
def test_run_up_to_date(
    monkeypatch,
    tmpdir,
    capsys,
    release,
    repository,
    request_json,
    expected,
):
    with tmpdir.as_cwd():
        arguments = [
            "script_name",
            "release_file",
            "repository_file",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        with open("repository_file", mode="w", encoding="utf-8") as fout:
            fout.write(str(repository))
        with open("release_file", mode="w", encoding="utf-8") as fout:
            fout.write(str(release))
        request_mock = MagicMock()
        request_mock.json.return_value = request_json
        monkeypatch.setattr(requests, "get", MagicMock(return_value=request_mock))

        check_up_to_date_pypi.main()
        print_message = capsys.readouterr().out
        assert (
            "dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0"
            in print_message
        )

        result = {}
        yaml = YAML()
        with open("new_file", encoding="utf-8") as fin:
            result["release"] = yaml.load(fin)
        with open("repository_file", encoding="utf-8") as fin:
            result["repo"] = yaml.load(fin)

        assert result == expected


@pytest.mark.parametrize(
    "release_file_content",
    [
        pytest.param(
            """
                    dummy_package_patch: 1.0.0
                    dummy_package_minor: 1.0.0
                    dummy_package_major: 1.0.0
                """,
            id="patch_minor_major",
        ),
        pytest.param(
            """
                    dummy_package_patch: 1.0.0
                    dummy_package_major: 1.0.0
                    dummy_package_minor: 1.0.0
                """,
            id="patch_major_minor",
        ),
        pytest.param(
            """
                    dummy_package_minor: 1.0.0
                    dummy_package_major: 1.0.0
                    dummy_package_patch: 1.0.0
                """,
            id="minor_major_patch",
        ),
    ],
)
def test_upgrade_type_grouping(release_file_content, tmpdir, monkeypatch, capsys):
    repository_file_content = """
    dummy_package_patch:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

    dummy_package_minor:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

    dummy_package_major:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout
    """

    with tmpdir.as_cwd():
        with open("repository_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(repository_file_content)
        with open("release_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(release_file_content)
        folder_name = os.getcwd()

        def side_effect(url: str, timeout):
            if "dummy_package_patch" in url.split("/"):
                request_mock = MagicMock()
                request_json = {
                    "releases": {"1.0.1": []},
                }
                request_mock.json.return_value = request_json
                return request_mock
            elif "dummy_package_minor" in url.split("/"):
                request_mock = MagicMock()
                request_json = {
                    "releases": {"1.1.0": []},
                }
                request_mock.json.return_value = request_json
                return request_mock
            elif "dummy_package_major" in url.split("/"):
                request_mock = MagicMock()
                request_json = {
                    "releases": {"2.0.0": []},
                }
                request_mock.json.return_value = request_json
                return request_mock
            else:
                raise ValueError(
                    f"INCORRECT PACKAGE NAME ENTERED! {str(url)} Called with timeout={timeout}"
                )

        arguments = [
            "script_name",
            f"{folder_name}/release_file.yml",
            f"{folder_name}/repository_file.yml",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=side_effect))
        check_up_to_date_pypi.main()
        system_print = capsys.readouterr().out

        assert (
            "Major upgrades:\ndummy_package_major not at latest pypi version: 2.0.0, is"
            " at: 1.0.0\n\nMinor upgrades:\ndummy_package_minor not at latest pypi"
            " version: 1.1.0, is at: 1.0.0\n\nPatch upgrades:\ndummy_package_patch not"
            " at latest pypi version: 1.0.1, is at: 1.0.0" in system_print
        )


@pytest.mark.parametrize(
    "release_file_content, ignore_argument",
    [
        pytest.param(
            """
                    dummy_package_patch: 1.0.0
                    dummy_package_minor: 1.0.0
                    dummy_package_major: 1.0.0
                    dummy_package_should_not_update: main
                """,
            "main",
            id="ignore_main_version",
        ),
        pytest.param(
            """
                    dummy_package_patch: 1.0.0
                    dummy_package_minor: 1.0.0
                    dummy_package_major: 1.0.0
                    dummy_package_should_not_update: 1.0.0
                """,
            "should_not_update",
            id="ignore_semantic_version",
        ),
    ],
)
def test_upgrade_ignore_flag(
    release_file_content, ignore_argument, tmpdir, monkeypatch, capsys
):
    repository_file_content = """
    dummy_package_patch:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

    dummy_package_minor:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

    dummy_package_major:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

    dummy_package_should_not_update:
      1.0.0:
        source: pypi
        make: pip
        maintainer: scout

      main:
        source: pypi
        make: pip
        maintainer: scout
    """

    with tmpdir.as_cwd():
        with open("repository_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(repository_file_content)
        with open("release_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(release_file_content)
        folder_name = os.getcwd()

    def side_effect(url: str, timeout):
        if "dummy_package_patch" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {"1.0.1": []},
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_minor" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {"1.1.0": []},
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_major" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {"2.0.0": []},
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_main_should_not_update" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {"4.4.3": []},
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_should_not_update" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {"2.0.0": []},
            }
            request_mock.json.return_value = request_json
            return request_mock
        else:
            raise ValueError(
                f"INCORRECT PACKAGE NAME ENTERED! {str(url)} Called with timeout={timeout}"
            )

    arguments = [
        "",
        f"{folder_name}/release_file.yml",
        f"{folder_name}/repository_file.yml",
        "--ignore",
        ignore_argument,
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(requests, "get", MagicMock(side_effect=side_effect))

    check_up_to_date_pypi.main()
    system_exit_message = capsys.readouterr().out
    assert "dummy_package_should_not_update" not in system_exit_message
    assert "dummy_package_main_should_not_update" not in system_exit_message
