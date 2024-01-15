from base64 import b64encode
from unittest import mock

import github
import pytest
import yaml

from komodo.insert_proposals import insert_proposals

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
        self.content = b64encode(bytes(dicty, "utf-8"))


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
