import functools
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
        pytest.param(
            {"1.0.0": [{"filename": "wheel_for_stub_platform.whl"}]},
            id="Just valid tag",
        ),
        pytest.param(
            {
                "1.0.0": [{"filename": "wheel_for_stub_platform.whl"}],
                "2.0.0a0": [{"filename": "wheel_for_stub_platform.whl"}],
            },
            id="Pre-release tag",
        ),
        pytest.param(
            {
                "1.0.0": [{"filename": "wheel_for_stub_platform.whl"}],
                "2.0.0.dev": [{"filename": "wheel_for_stub_platform.whl"}],
            },
            id="Dev tag",
        ),
        pytest.param(
            {
                "1.0.0": [{"filename": "wheel_for_stub_platform.whl"}],
                "2.0.0": [
                    {
                        "filename": "wheel_for_stub_platform.whl",
                        "requires_python": ">3.7",
                    }
                ],
            },
            id="Too high python requirement on 2.0",
        ),
        pytest.param(
            {
                "1.0.0": [
                    {"requires_python": ">3", "filename": "wheel_for_stub_platform.whl"}
                ],
                "2.0.0": [
                    {
                        "requires_python": ">3.7",
                        "filename": "wheel_for_stub_platform.whl",
                    }
                ],
            },
            id="Latest version not compatible",
        ),
    ],
)
def test_compatible_versions(input_dict):
    result = compatible_versions(input_dict, "3.6.10", "stub_platform")
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
    insert_upgrade_proposals(suggestions, repository, release)
    assert expected == {"release": release, "repo": repository}


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
    result = get_upgrade_proposals_from_pypi(
        release, repository, "3.6.8", "stub_platform"
    )
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
        with open(
            "release_file.yml", mode="w", encoding="utf-8"
        ) as release_file_stream:
            yaml.dump(
                {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
                release_file_stream,
            )
        with open(
            "repository_file.yml", mode="w", encoding="utf-8"
        ) as repository_file_stream:
            yaml.dump(
                {
                    "dummy_package": {"1.0.0": {"source": "pypi"}},
                    "custom_package": {"1.1.1": {"maintainer": "some_person"}},
                },
                repository_file_stream,
            )
        request_mock = MagicMock()
        request_mock.json.return_value = {
            "releases": {
                "2.2.0": [{"yanked": True}],
                "2.0.0": [
                    {
                        "requires_python": ">=3.8",
                        "filename": f"valid_upgrade_for_macos_{sys.platform}",
                    }
                ],
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
                "releases": {
                    "2.0.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
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
                "releases": {
                    "2.0.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
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
                "releases": {
                    "2.2.0": [{"yanked": True}],
                    "2.0.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}],
                },
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
                    "releases": {
                        "1.0.1": [
                            {"filename": f"valid_upgrade_for_macos_{sys.platform}"}
                        ]
                    },
                }
                request_mock.json.return_value = request_json
                return request_mock
            elif "dummy_package_minor" in url.split("/"):
                request_mock = MagicMock()
                request_json = {
                    "releases": {
                        "1.1.0": [
                            {"filename": f"valid_upgrade_for_macos_{sys.platform}"}
                        ]
                    },
                }
                request_mock.json.return_value = request_json
                return request_mock
            elif "dummy_package_major" in url.split("/"):
                request_mock = MagicMock()
                request_json = {
                    "releases": {
                        "2.0.0": [
                            {"filename": f"valid_upgrade_for_macos_{sys.platform}"}
                        ]
                    },
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
                "releases": {
                    "1.0.1": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_minor" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "1.1.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_major" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "2.0.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_main_should_not_update" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "4.4.3": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_should_not_update" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "2.0.0": [{"filename": f"valid_upgrade_for_macos_{sys.platform}"}]
                },
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


def create_stub_files(tmpdir) -> str:
    stub_release_file_content = """
        dummy_package_compatible_upgrade_exists: 1.0.0
        dummy_package_compatible_upgrade_does_not_exist: 1.0.0
    """

    stub_repository_file_content = """
        dummy_package_compatible_upgrade_exists:
          1.0.0:
            source: pypi
            make: pip
            maintainer: scout

        dummy_package_compatible_upgrade_does_not_exist:
          1.0.0:
            source: pypi
            make: pip
            maintainer: scout
    """
    with tmpdir.as_cwd():
        with open("repository_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(stub_repository_file_content)
        with open("release_file.yml", mode="w", encoding="utf-8") as fout:
            fout.write(stub_release_file_content)
        return os.getcwd()


def side_effect(url: str, timeout, target_platform):
    request_mock = MagicMock()
    if "dummy_package_compatible_upgrade_exists" in url.split("/"):
        request_json = {
            "releases": {
                "1.1.0": [{"filename": f"valid_upgrade_for_macos_{target_platform}"}],
            },
        }
    elif "dummy_package_compatible_upgrade_does_not_exist" in url.split("/"):
        request_json = {
            "releases": {
                "1.1.0": [{"filename": "valid_upgrade_for_different_os"}],
                "1.0.0": [
                    {"filename": f"valid_old_version_for_macos_{target_platform}"}
                ],
            },
        }
    else:
        raise ValueError(
            f"INCORRECT PACKAGE NAME ENTERED! {str(url)} Called with timeout={timeout}"
        )
    request_mock.json.return_value = request_json
    return request_mock


@pytest.mark.parametrize(
    "target_platform",
    [
        pytest.param("darwin", id="macos"),
        pytest.param("win32", id="windows"),
        pytest.param("linux", id="linux"),
        pytest.param("linux2", id="linux2"),
    ],
)
def test_suggestor_filters_out_os_incompatible_versions_for_host_platform_by_default(
    target_platform, tmpdir, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "platform", target_platform)

    folder_name = create_stub_files(tmpdir)

    arguments = [
        "",
        f"{folder_name}/release_file.yml",
        f"{folder_name}/repository_file.yml",
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(
        requests,
        "get",
        MagicMock(
            side_effect=functools.partial(side_effect, target_platform=target_platform)
        ),
    )
    check_up_to_date_pypi.main()
    system_exit_message = capsys.readouterr().out
    assert "dummy_package_compatible_upgrade_exists" in system_exit_message
    assert "dummy_package_compatible_upgrade_does_not_exist" not in system_exit_message


@pytest.mark.parametrize(
    "target_platform",
    [
        pytest.param("darwin", id="macos"),
        pytest.param("win32", id="windows"),
        pytest.param("linux", id="linux"),
        pytest.param("linux2", id="linux2"),
    ],
)
def test_suggestor_filters_out_os_incompatible_versions_on_specific_platform_flag(
    target_platform, tmpdir, monkeypatch, capsys
):
    folder_name = create_stub_files(tmpdir)

    arguments = [
        "",
        f"{folder_name}/release_file.yml",
        f"{folder_name}/repository_file.yml",
        "--target-platform",
        target_platform,
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(
        requests,
        "get",
        MagicMock(
            side_effect=functools.partial(side_effect, target_platform=target_platform)
        ),
    )
    check_up_to_date_pypi.main()
    system_exit_message = capsys.readouterr().out
    assert "dummy_package_compatible_upgrade_exists" in system_exit_message
    assert "dummy_package_compatible_upgrade_does_not_exist" not in system_exit_message


@pytest.mark.parametrize(
    "filename",
    ["package_sdist.tar.gz", "universal_wheel-none-any.whl"],
)
def test_suggestor_shows_platform_independent_packages_and_source_distributions(
    filename, tmpdir, monkeypatch, capsys
):
    folder_name = create_stub_files(tmpdir)

    arguments = [
        "",
        f"{folder_name}/release_file.yml",
        f"{folder_name}/repository_file.yml",
    ]
    monkeypatch.setattr(sys, "argv", arguments)

    def side_effect(url: str, timeout):
        request_mock = MagicMock()
        if "dummy_package_compatible_upgrade_exists" in url.split("/"):
            request_json = {
                "releases": {
                    "1.1.0": [{"filename": f"{filename}"}],
                },
            }
        elif "dummy_package_compatible_upgrade_does_not_exist" in url.split("/"):
            request_json = {
                "releases": {
                    "1.1.0": [{"filename": "valid_upgrade_for_different_os"}],
                    "1.0.0": [
                        {"filename": f"valid_old_version_for_macos_{sys.platform}"}
                    ],
                },
            }
        else:
            raise ValueError(
                f"INCORRECT PACKAGE NAME ENTERED! {str(url)} Called with timeout={timeout}"
            )
        request_mock.json.return_value = request_json
        return request_mock

    monkeypatch.setattr(
        requests,
        "get",
        MagicMock(side_effect=side_effect),
    )
    check_up_to_date_pypi.main()
    system_exit_message = capsys.readouterr().out
    assert "dummy_package_compatible_upgrade_exists" in system_exit_message
    assert "dummy_package_compatible_upgrade_does_not_exist" not in system_exit_message


@pytest.mark.parametrize(
    "flag, expected_messages, unexpected_messages",
    [
        pytest.param(
            "--patch-upgrade",
            ["dummy_package_patch"],
            ["dummy_package_minor", "dummy_package_major"],
            id="Upgrade_patch_versions",
        ),
        pytest.param(
            "--minor-upgrade",
            ["dummy_package_minor", "dummy_package_patch"],
            ["dummy_package_major"],
            id="Upgrade_minor_and_patch_versions",
        ),
    ],
)
def test_upgrade_specific_versions_flag(
    flag, expected_messages, unexpected_messages, tmpdir, monkeypatch, capsys
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
    """

    release_file_content = """
                    dummy_package_patch: 1.0.0
                    dummy_package_minor: 1.0.0
                    dummy_package_major: 1.0.0
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
                "releases": {
                    "1.0.1": [{"filename": f"wheel_for_macos_{sys.platform}.whl"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_minor" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "1.1.0": [{"filename": f"wheel_for_macos_{sys.platform}.whl"}]
                },
            }
            request_mock.json.return_value = request_json
            return request_mock
        elif "dummy_package_major" in url.split("/"):
            request_mock = MagicMock()
            request_json = {
                "releases": {
                    "2.0.0": [{"filename": f"wheel_for_macos_{sys.platform}.whl"}]
                },
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
        flag,
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(requests, "get", MagicMock(side_effect=side_effect))

    check_up_to_date_pypi.main()
    system_exit_message = capsys.readouterr().out
    for message in expected_messages:
        assert message in system_exit_message
    for message in unexpected_messages:
        assert message not in system_exit_message
