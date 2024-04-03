from base64 import b64encode
from contextlib import ExitStack as does_not_raise
from unittest import mock

import github
import pytest
import yaml

from komodo.insert_proposals import (
    clean_proposals_file,
    create_new_release_file,
    create_pr_with_changes,
    generate_contents_of_new_release_matrix,
    insert_proposals,
    recursive_update,
    validate_upgrades,
)
from komodo.yaml_file_types import RepositoryFile

VALID_REPOSITORY_CONTENT = {
    "addlib": {
        "1.1.3": {"source": "pypi", "make": "pip", "maintainer": "scout"},
        "1.1.2": {"source": "pypi", "make": "pip", "maintainer": "scout"},
        "1.1.1": {"source": "pypi", "make": "pip", "maintainer": "scout"},
    },
    "testlib2": {
        "3.7": {"source": "pypi", "make": "pip", "maintainer": "scout"},
        "1.1.2": {"source": "pypi", "make": "pip", "maintainer": "scout"},
        "1.1.1": {"source": "pypi", "make": "pip", "maintainer": "scout"},
    },
}


class MockContent:
    def __init__(self, dicty) -> None:
        self.sha = "testsha"
        self.content = b64encode(yaml.dump(dicty).encode())


class MockRepo:
    existing_branches = ["git_ref", "2222.22.rc1", "2222.22.rc2"]

    def __init__(self, files) -> None:
        self.files = files
        self.updated_files = {}
        self.created_pulls = {}

    def get_contents(self, filename, ref):
        if filename in self.files:
            return MockContent(self.files[filename])
        else:
            msg = f"unexpected call with file {filename} and ref {ref}"
            raise ValueError(msg)

    def get_branch(self, ref):
        if ref in MockRepo.existing_branches:
            output_mock = mock.Mock()
            output_mock.commit.sha = "testsha1"
            return output_mock
        else:
            raise github.GithubException(None, None, None)

    def create_git_ref(self, ref, sha):
        _mock = mock.Mock()
        _mock.ref = ref
        _mock.sha = sha
        return _mock

    def create_file(self, target_file, msg, content, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {
            "content": yaml.load(content, Loader=yaml.CLoader),
            "branch": branch,
            "msg": msg,
        }

    def update_file(self, target_file, msg, content, sha, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {
            "content": yaml.load(content, Loader=yaml.CLoader),
            "branch": branch,
            "msg": msg,
            "sha": sha,
        }

    def create_pull(self, title, body, head, base):
        output_mock = mock.Mock()
        self.created_pulls[title] = {"head": head, "body": body, "base": base}
        return output_mock


@pytest.mark.parametrize(
    (
        "base",
        "target",
        "repo_files",
        "changed_files",
        "pull_requests",
        "return_type",
        "error_message",
    ),
    [
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"testlib2": "ignore"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"testlib2": "ignore"},
                },
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="empty_upgrade_proposal",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": {"testlib2": "1.1.2", "addlib": "1.1.3"},
                    "1111-12": {"testlib2": "ignore"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.2",
                    "addlib": "1.1.3",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"testlib2": "ignore"},
                },
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="with_upgrade_proposal",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": {
                        "testlib2": {
                            "rhel7": {"py38": "1.1.2"},
                            "rhel8": {"py38": "1.1.1", "py311": "1.1.2"},
                        },
                    },
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": {
                        "rhel7": {"py38": "1.1.2"},
                        "rhel8": {"py38": "1.1.1", "py311": "1.1.2"},
                    },
                },
                "upgrade_proposals.yml": {"1111-11": None},
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="update_from_version_to_full_matrix",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": {"testlib2": {"py38": "1.1.2", "py311": "1.1.1"}},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": {"py38": "1.1.2", "py311": "1.1.1"},
                },
                "upgrade_proposals.yml": {"1111-11": None},
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="update_from_version_to_py_matrix",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": {
                        "rhel7": {"py38": "1.1.2"},
                        "rhel8": {"py38": "1.1.1", "py311": "1.1.2"},
                    },
                },
                "upgrade_proposals.yml": {
                    "1111-11": {"testlib2": "1.1.2"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.2",
                },
                "upgrade_proposals.yml": {"1111-11": None},
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="update_from_matrix_to_version",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.11.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": {
                        "testlib2": {"py38": None, "py311": "1.1.2"},
                    },
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": {"py38": None, "py311": "1.1.2"},
                },
                "upgrade_proposals.yml": {"1111-11": None},
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            "",
            id="remove_package_from_one_py_version",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc2",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": {"testlib2": "1.1.2"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {},
            [],
            AssertionError,
            r"No section for this release \(1111-12\) in upgrade_proposals\.yml",
            id="missing_proposal_heading",
        ),
        pytest.param(
            MockRepo.existing_branches[-2],
            MockRepo.existing_branches[-1],
            {},
            {},
            [],
            ValueError,
            "Branch 2222.22.rc2 exists already",
            id="branch_already_exists",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"addlib": "1.1.4"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {},
            [],
            SystemExit,
            "Version '1.1.4' of package 'addlib' not found in repository",
            id="upgrade_proposal_new_version_not_present_in_repository",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"package_does_not_exist": "1.1.4"},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {},
            [],
            SystemExit,
            "Package 'package_does_not_exist' not found in repository",
            id="upgrade_proposal_new_package_not_present_in_repository",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"testlib2": 3.7},
                },
                "repository.yml": VALID_REPOSITORY_CONTENT,
            },
            {},
            [],
            SystemExit,
            r"invalid version type ",
            id="float_version_number_in_proposal",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"addlib": "1.1.2"},
                },
                "repository.yml": {
                    "addlib": {
                        3.7: {"source": "pypi", "make": "pip", "maintainer": "scout"},
                        "1.1.2": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "1.1.1": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                    },
                },
            },
            {},
            [],
            SystemExit,
            r"has invalid version type",
            id="float_version_number_in_repository",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"addlib": "1.1.2"},
                },
                "repository.yml": {
                    "addlib": {
                        "3.7": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "v1.1.2": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "1.1.1": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                    },
                },
            },
            {},
            [],
            SystemExit,
            r"Did you mean 'v1.1.2'",
            id="mismatching_version_format",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": {
                    "Testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"Addlib": "1.1.2"},
                },
                "repository.yml": {
                    "addlib": {
                        "3.7": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "1.1.2": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                        "1.1.1": {
                            "source": "pypi",
                            "make": "pip",
                            "maintainer": "scout",
                        },
                    },
                },
            },
            {},
            [],
            SystemExit,
            r"not found in repository. Did you mean",
            id="mismatching_casing_files",
        ),
    ],
)
def test_insert_proposals(
    base,
    target,
    repo_files,
    changed_files,
    pull_requests,
    return_type,
    error_message,
):
    repo = MockRepo(files=repo_files)

    if isinstance(return_type(), Exception):
        with pytest.raises(return_type, match=error_message):
            insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")
    elif isinstance(return_type(), SystemExit):
        with pytest.raises(SystemExit, match=error_message):
            insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")
    else:
        insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")

    assert len(changed_files) == len(repo.updated_files)
    for file, content in changed_files.items():
        assert file in repo.updated_files
        assert repo.updated_files[file]["content"] == content

    assert len(pull_requests) == len(repo.created_pulls)
    for pull_request in pull_requests:
        assert pull_request in repo.created_pulls


class MockContentYaml:
    def __init__(self, dicty) -> None:
        self.sha = "testsha"
        print(f"{dicty=}")
        self.content = b64encode(bytes(dicty, encoding="utf-8"))


class MockRepoYaml:
    existing_branches = ["git_ref", "2222.22.rc1", "2222.22.rc2"]

    def __init__(self, files) -> None:
        self.files = files
        self.updated_files = {}
        self.created_pulls = {}

    def get_contents(self, filename, ref):
        if filename in self.files:
            return MockContentYaml(self.files[filename])
        else:
            msg = f"unexpected call with file {filename} and ref {ref}"
            raise ValueError(msg)

    def get_branch(self, ref):
        if ref in MockRepoYaml.existing_branches:
            output_mock = mock.Mock()
            output_mock.commit.sha = "testsha1"
            return output_mock
        else:
            raise github.GithubException(None, None, None)

    def create_git_ref(self, ref, sha):
        _mock = mock.Mock()
        _mock.ref = ref
        _mock.sha = sha
        return _mock

    def create_file(self, target_file, msg, content, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {
            "content": yaml.load(content, Loader=yaml.CLoader),
            "branch": branch,
            "msg": msg,
        }

    def update_file(self, target_file, msg, content, sha, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {
            "content": yaml.load(content, Loader=yaml.CLoader),
            "branch": branch,
            "msg": msg,
            "sha": sha,
        }

    def create_pull(self, title, body, head, base):
        output_mock = mock.Mock()
        self.created_pulls[title] = {"head": head, "body": body, "base": base}
        return output_mock


@pytest.mark.parametrize(
    (
        "base",
        "target",
        "repo_files",
        "changed_files",
        "pull_requests",
        "return_type",
        "error_message",
    ),
    [
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": """
                    "testlib1": "1.1.1"
                    "testlib2": "1.1.1"
                """,
                "upgrade_proposals.yml": """
                    "1111-11":
                    "1111-12":
                      "addlib": "1.1.2"
                """,
                "repository.yml": """
                    "addlib":
                      "1.1.2":
                        "source": "pypi"
                        "make": "pip"
                        "maintainer": "scout"
                    "addlib":
                      "1.1.2":
                        "source": "pypi"
                        "make": "pip"
                        "maintainer": "scout"

                """,
            },
            {},
            [],
            SystemExit,
            r"found duplicate key \"addlib\"",
            id="duplicate_packages_in_repository",
        ),
        pytest.param(
            "1111.11.rc1",
            "1111.12.rc1",
            {
                "releases/matrices/1111.11.rc1.yml": """
                    "testlib1": "1.1.1"
                    "testlib2": "1.1.1"
                """,
                "upgrade_proposals.yml": """
                    "1111-11": None,
                    "1111-12":
                      "addlib": "1.1.2"
                      "addlib": "1.2.0"
                """,
                "repository.yml": """
                    "addlib":
                      "1.1.2":
                        "source": "pypi"
                        "make": "pip"
                        "maintainer": "scout"
                    "addlib2":
                      "1.1.2":
                        "source": "pypi"
                        "make": "pip"
                        "maintainer": "scout"

                """,
            },
            {},
            [],
            SystemExit,
            r"found duplicate key \"addlib\"",
            id="duplicate_packages_in_upgrade_proposals",
        ),
    ],
)
def test_duplicate_package_entry_handling(
    base,
    target,
    repo_files,
    changed_files,
    pull_requests,
    return_type,
    error_message,
):
    repo = MockRepoYaml(files=repo_files)

    if isinstance(return_type(), Exception):
        with pytest.raises(return_type, match=error_message):
            insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")
    elif isinstance(return_type(), SystemExit):
        with pytest.raises(SystemExit, match=error_message):
            insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")
    else:
        insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")

    assert len(changed_files) == len(repo.updated_files)
    for file, content in changed_files.items():
        assert file in repo.updated_files
        assert repo.updated_files[file]["content"] == content

    assert len(pull_requests) == len(repo.created_pulls)
    for pull_request in pull_requests:
        assert pull_request in repo.created_pulls


@pytest.mark.parametrize(
    "release_dict, upgrade_dict, expected_dict",
    [
        pytest.param(
            {"package_a": "version_a"},
            {"package_a": "version_b"},
            {"package_a": "version_b"},
            id="update_version",
        ),
        pytest.param(
            {"package_a": "version_a"}, {}, {"package_a": "version_a"}, id="no_update"
        ),
        pytest.param(
            {"package_a": "version_a"},
            {"package_b": "version_a"},
            {"package_a": "version_a", "package_b": "version_a"},
            id="update_with_new_package",
        ),
        pytest.param(
            {"package_a": {"py38": "version_a"}},
            {"package_a": {"py38": "version_b"}},
            {"package_a": {"py38": "version_b"}},
            id="update_one_level_deep_matrix",
        ),
        pytest.param(
            {"package_a": {"rhel8": {"py38": "version_a"}}},
            {"package_a": {"rhel8": {"py38": "version_b"}}},
            {"package_a": {"rhel8": {"py38": "version_b"}}},
            id="update_two_level_deep_matrix",
        ),
        pytest.param(
            {"package_a": {"rhel8": {"py38": "version_a"}}},
            {"package_a": "version_b"},
            {"package_a": "version_b"},
            id="update_from_matrix_to_version",
        ),
        pytest.param(
            {"package_a": "version_a"},
            {"package_a": {"rhel8": {"py38": "version_b"}}},
            {"package_a": {"rhel8": {"py38": "version_b"}}},
            id="update_from_version_to_matrix",
        ),
        pytest.param(
            {"package_a": {"py38": "version_a", "py312": "version_b"}},
            {"package_a": {"py38": "version_b"}},
            {"package_a": {"py38": "version_b", "py312": "version_b"}},
            id="update_only_one_matrix_version_one_level_deep",
        ),
        pytest.param(
            {
                "package_a": {
                    "rhel7": {"py38": "version_a", "py312": "version_b"},
                    "rhel8": "version_b",
                }
            },
            {"package_a": {"rhel8": {"py38": "version_b"}}},
            {
                "package_a": {
                    "rhel7": {"py38": "version_a", "py312": "version_b"},
                    "rhel8": {"py38": "version_b"},
                }
            },
            id="update_only_one_matrix_version_two_levels_deep",
        ),
        pytest.param(
            {
                "package_a": {
                    "rhel7": {"py38": "version_a", "py312": None},
                    "rhel8": {"py38": "version_b"},
                }
            },
            {"package_a": {"rhel8": {"py38": None, "py312": None}}},
            {
                "package_a": {
                    "rhel7": {"py38": "version_a", "py312": None},
                    "rhel8": {"py38": None, "py312": None},
                }
            },
            id="none_versions",
        ),
    ],
)
def test_recursive_update(release_dict, upgrade_dict, expected_dict):
    recursive_update(release_dict, upgrade_dict)
    assert release_dict == expected_dict


@pytest.mark.parametrize(
    "upgrade_section, repofile_content, expectation",
    [
        pytest.param(
            {"package1": "1.0.1", "package2": "2.0.3"},
            {
                "package1": {
                    "1.0.1": {"make": "pip", "maintainer": "scout"},
                    "1.0.0": {"make": "pip", "maintainer": "scout"},
                },
                "package2": {
                    "2.0.3": {
                        "make": "pip",
                        "maintainer": "scout",
                        "depends": ["package1"],
                    },
                    "2.0.2": {
                        "make": "pip",
                        "maintainer": "scout",
                        "depends": ["package1"],
                    },
                },
            },
            does_not_raise(),
            id="validate_upgrades_does_not_raise",
        ),
        pytest.param(
            {"package1": "1.0.2"},
            {
                "package1": {
                    "1.0.1": {"make": "pip", "maintainer": "scout"},
                    "1.0.0": {"make": "pip", "maintainer": "scout"},
                },
                "package2": {
                    "2.0.3": {
                        "make": "pip",
                        "maintainer": "scout",
                        "depends": ["package1"],
                    },
                    "2.0.2": {
                        "make": "pip",
                        "maintainer": "scout",
                        "depends": ["package1"],
                    },
                },
            },
            pytest.raises(
                SystemExit,
                match=r"Version '1.0.2' of package 'package1' not found in repository.",
            ),
            id="validate_upgrades_raises_systemexit_on_missing_package_version",
        ),
    ],
)
def test_validate_upgrades(upgrade_section, repofile_content, expectation):
    repofile = RepositoryFile()
    repofile.content = repofile_content
    with expectation:
        validate_upgrades(upgrade_section, repofile)


@pytest.mark.parametrize(
    "upgrade, expected_result",
    [
        pytest.param(
            {"package3": "1.0.2"},
            {
                "package1": "1.0.0",
                "package2": "2.0.3",
                "package3": "1.0.2",
                "package4": {"rhel7": "0.0.9", "rhel8": "0.0.9"},
            },
            id="addition_of_new_package",
        ),
        pytest.param(
            {"package1": "1.0.1"},
            {
                "package1": "1.0.1",
                "package2": "2.0.3",
                "package4": {"rhel7": "0.0.9", "rhel8": "0.0.9"},
            },
            id="upgrade_package_version",
        ),
        pytest.param(
            {"package1": {"rhel7": "1.0.0", "rhel8": "1.0.1"}},
            {
                "package1": {"rhel7": "1.0.0", "rhel8": "1.0.1"},
                "package2": "2.0.3",
                "package4": {"rhel7": "0.0.9", "rhel8": "0.0.9"},
            },
            id="change_from_version_to_version_matrix",
        ),
        pytest.param(
            {"package4": "1.0.0"},
            {
                "package1": "1.0.0",
                "package2": "2.0.3",
                "package4": "1.0.0",
            },
            id="change_from_version_matrix_to_version",
        ),
        pytest.param(
            None,
            {
                "package1": "1.0.0",
                "package2": "2.0.3",
                "package4": {"rhel7": "0.0.9", "rhel8": "0.0.9"},
            },
            id="no_upgrade",
        ),
    ],
)
def test_generate_contents_of_new_release_returns_valid(upgrade, expected_result):
    release_matrix_file_content = {
        "package1": "1.0.0",
        "package2": "2.0.3",
        "package4": {"rhel7": "0.0.9", "rhel8": "0.0.9"},
    }
    repository_file_content = {
        "package1": {
            "1.0.1": {"make": "pip", "maintainer": "scout"},
            "1.0.0": {"make": "pip", "maintainer": "scout"},
        },
        "package2": {
            "2.0.3": {
                "make": "pip",
                "maintainer": "scout",
                "depends": ["package1"],
            },
            "2.0.2": {
                "make": "pip",
                "maintainer": "scout",
                "depends": ["package1"],
            },
        },
        "package3": {"1.0.2": {"make": "pip", "maintainer": "scout"}},
        "package4": {
            "1.0.0": {"make": "pip", "maintainer": "scout"},
            "0.0.9": {"make": "pip", "maintainer": "scout"},
        },
    }
    repofile = RepositoryFile()
    repofile.content = repository_file_content
    result = generate_contents_of_new_release_matrix(
        release_matrix_file_content, repofile, upgrade
    )
    assert result == yaml.dump(expected_result)


@pytest.mark.parametrize(
    "propose_upgrade_content, upgrade_key, expected_upgrade_proposals_end_content",
    [
        pytest.param(
            {
                "1111-11": {"testlib2": "1.1.1"},
                "1111-12": {"testlib2": "1.1.2"},
            },
            "1111-11",
            {
                "1111-11": None,
                "1111-12": {"testlib2": "1.1.2"},
            },
            id="clean_upgrade_older_release",
        ),
        pytest.param(
            {
                "1111-11": None,
                "1111-12": {"testlib2": "1.1.2"},
            },
            "1111-11",
            {
                "1111-11": None,
                "1111-12": {"testlib2": "1.1.2"},
            },
            id="clean_empty_upgrade",
        ),
        pytest.param(
            {
                "1111-11": None,
                "1111-12": {"testlib2": {"rhel7": "1.1.1", "rhel8": "1.1.0"}},
            },
            "1111-12",
            {
                "1111-11": None,
                "1111-12": None,
            },
            id="clean_nested_upgrade",
        ),
        pytest.param(
            {
                "1111-11": {"testlib2": "1.1.1"},
                "1111-12": {"testlib2": "1.1.2"},
            },
            "1111-12",
            {
                "1111-11": {"testlib2": "1.1.1"},
                "1111-12": None,
            },
            id="clean_upgrade",
        ),
    ],
)
def test_clean_proposals_file(
    propose_upgrade_content, upgrade_key, expected_upgrade_proposals_end_content
):
    repo_files = {
        "releases/matrices/1111.11.rc1.yml": {
            "testlib1": "1.1.1",
            "testlib2": "1.1.1",
        },
        "upgrade_proposals.yml": propose_upgrade_content,
        "repository.yml": VALID_REPOSITORY_CONTENT,
    }
    repo = MockRepo(files=repo_files)
    clean_proposals_file(
        propose_upgrade_content, upgrade_key, repo, "git_ref", "tmp_target"
    )
    assert propose_upgrade_content == expected_upgrade_proposals_end_content
    assert (
        repo.updated_files["upgrade_proposals.yml"]["content"]
        == expected_upgrade_proposals_end_content
    )


def test_create_pr_with_changes():
    mock_repo = MockRepo({})
    tmp_ref = mock.Mock()
    create_pr_with_changes(
        mock_repo, mock.Mock(), "target", "from_sha", "tmp_target", tmp_ref, "pr_msg"
    )
    tmp_ref.delete.assert_called_once()
    assert len(mock_repo.created_pulls.keys()) == 2
    assert "Add release target" in mock_repo.created_pulls
    assert "Temporary PR target" in mock_repo.created_pulls


def test_create_new_release_file():
    mock_repo = MockRepo({})
    stub_file_content = "setuptools: 0.14.9\npython: 3.8.6"
    new_release_file_name = create_new_release_file(
        mock_repo, "1111.11", stub_file_content, "branchy"
    )
    assert new_release_file_name == "releases/matrices/1111.11.yml"
    assert mock_repo.updated_files[new_release_file_name]["content"] == yaml.load(
        stub_file_content, Loader=yaml.CLoader
    )
