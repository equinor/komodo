from unittest import mock
from komodo.insert_proposals import insert_proposals
import yaml
from base64 import b64encode
import pytest
import github


class MockContent(object):
    def __init__(self, dicty):
        self.sha = "testsha"
        self.content = b64encode(yaml.dump(dicty).encode())


class MockRepo(object):
    existing_branches = ["git_ref", "2222.22.rc1", "2222.22.rc2"]

    def __init__(self, files):
        self.files = files
        self.updated_files = {}
        self.created_pulls = {}

    def get_contents(self, filename, ref):
        if filename in self.files:
            return MockContent(self.files[filename])
        else:
            raise ValueError(f"unexpected call with file {filename}")

    def get_branch(self, ref):
        if ref in MockRepo.existing_branches:
            o = mock.Mock()
            o.commit.sha = "testsha1"
            return o
        else:
            raise github.GithubException(None, None, None)

    def create_git_ref(self, ref, sha):
        o = mock.Mock()
        return o

    def create_file(self, target_file, msg, content, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {"content": yaml.load(content), "branch": branch}

    def update_file(self, target_file, msg, content, sha, branch):
        assert target_file not in self.updated_files
        self.updated_files[target_file] = {"content": yaml.load(content), "branch": branch}

    def create_pull(self, title, body, head, base):
        o = mock.Mock()
        self.created_pulls[title] = {"head": head}
        return o


@pytest.mark.parametrize(
    "base, target, repo_files, changed_files, prs, return_type",
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
            },
            {
                "releases/matrices/1111.11.rc2.yml": {
                    "testlib1": "1.1.1",
                    "testlib2": "1.1.1",
                },
                "upgrade_proposals.yml": {
                    "1111-11": None,
                    "1111-12": {"testlib2": "ignore"},
                }
            },
            ["Temporary PR 1111.11.rc2", "Add release 1111.11.rc2"],
            type(None),
            id="empty_upgrade_proposal"
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
                    "1111-12": {"testlib2": "ignore"},
                },
            },
            {},
            [],
            ValueError,
            id="missing_proposal_heading",
        ),
        pytest.param(
            MockRepo.existing_branches[-2],
            MockRepo.existing_branches[-1],
            {},
            {},
            [],
            ValueError,
            id="branch_already_exists",
        )
    ],
)
def test_insert_proposals(base, target, repo_files, changed_files, prs, return_type):
    repo = MockRepo(files=repo_files)
    status = insert_proposals(repo, base, target, "git_ref", "jobname", "joburl")

    assert isinstance(status, return_type)

    assert len(changed_files) == len(repo.updated_files)
    for file, content in changed_files.items():
        assert file in repo.updated_files
        assert repo.updated_files[file]["content"] == content

    assert len(prs) == len(repo.created_pulls)
    for pr in prs:
        assert pr in repo.created_pulls
