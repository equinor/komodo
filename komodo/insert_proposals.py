import argparse
import collections
import contextlib
import difflib
import os
from base64 import b64decode
from datetime import datetime
from typing import Any

import github
from github import Github, UnknownObjectException
from github.ContentFile import ContentFile
from github.Repository import Repository

from komodo.prettier import write_to_string
from komodo.yaml_file_types import (
    KomodoException,
    ReleaseFile,
    RepositoryFile,
    UpgradeProposalsFile,
)


def recursive_update(left: Any, right: Any) -> Any:
    if right is None:
        return None
    for k, v in right.items():
        if isinstance(v, collections.abc.Mapping):
            d_val = left.get(k)
            if not d_val:
                left[k] = v
            else:
                recursive_update(d_val, v)
        else:
            left[k] = v
    return left


def _get_repo(token: str, fork: str, repo: str) -> Repository:
    client = Github(token)
    try:
        return client.get_repo(f"{fork}/{repo}")
    except UnknownObjectException:
        org = client.get_organization(fork)
        return org.get_repo(repo)


def diff_file_and_string(
    file_contents: str, string: str, leftname: str, rightname: str
) -> str:
    return "".join(
        difflib.unified_diff(
            file_contents.splitlines(True),
            string.splitlines(True),
            leftname,
            rightname,
            n=0,
        ),
    )


def load_yaml_from_repo(filename: str, repo: Repository, ref: str) -> bytes:
    sym_conf_content = repo.get_contents(filename, ref=ref)
    assert isinstance(sym_conf_content, ContentFile)
    return b64decode(sym_conf_content.content)


def main() -> None:
    args = parse_args()
    repo = _get_repo(os.environ["GITHUB_TOKEN"], args.git_fork, args.git_repo)
    insert_proposals(
        repo,
        args.base,
        args.target,
        args.git_ref,
        args.jobname,
        args.joburl,
    )


def verify_branch_does_not_exist(repo: Repository, branch_name: str) -> None:
    try:
        repo.get_branch(branch_name)
    except github.GithubException:
        pass
    else:
        msg = f"Branch {branch_name} exists already"
        raise ValueError(msg)


def insert_proposals(
    repo: Repository, base: str, target: str, git_ref: str, jobname: str, joburl: str
) -> None:
    year = target.split(".")[0]
    month = target.split(".")[1]
    tmp_target = target + ".tmp"

    # check that the branches do not already exist
    verify_branch_does_not_exist(repo, target)
    verify_branch_does_not_exist(repo, tmp_target)

    # create contents of new release
    proposals_yaml_string = load_yaml_from_repo("upgrade_proposals.yml", repo, git_ref)
    proposal_file = UpgradeProposalsFile().from_yaml_string(proposals_yaml_string)
    upgrade_key = f"{year}-{month}"
    upgrade = proposal_file.content.get(upgrade_key)
    proposal_file.validate_upgrade_key(upgrade_key)

    base_file = f"releases/matrices/{base}.yml"
    target_file = f"releases/matrices/{target}.yml"
    repofile_yaml_string = load_yaml_from_repo("repository.yml", repo, git_ref)
    repofile = RepositoryFile().from_yaml_string(repofile_yaml_string)
    release_file_yaml_string = load_yaml_from_repo(base_file, repo, git_ref)
    base_dict = ReleaseFile().from_yaml_string(release_file_yaml_string)
    if upgrade:
        errors = []
        for package_name, package_version in upgrade.items():
            try:
                repofile.validate_package_entry(package_name, package_version)
            except KomodoException as e:
                errors.append(e.error)
        if errors:
            raise SystemExit("\n".join(map(str, errors)))
    recursive_update(base_dict.content, upgrade)
    result = write_to_string(base_dict.content)

    # create new release file
    from_sha = repo.get_branch(git_ref).commit.sha
    tmp_ref = repo.create_git_ref(ref="refs/heads/" + tmp_target, sha=from_sha)
    repo.create_file(
        target_file,
        f"Add release {target}",
        result,
        branch=tmp_target,
    )

    # clean the proposal file
    proposal_file.content[upgrade_key] = None
    cleaned_upgrade = write_to_string(proposal_file.content, False)
    upgrade_contents = repo.get_contents("upgrade_proposals.yml", ref=git_ref)
    assert isinstance(upgrade_contents, ContentFile)

    repo.update_file(
        "upgrade_proposals.yml",
        "Clean proposals",
        cleaned_upgrade,
        sha=upgrade_contents.sha,
        branch=tmp_target,
    )

    # making PR
    base_content = repo.get_contents(base_file, ref=git_ref)
    assert isinstance(base_content, ContentFile)
    diff = diff_file_and_string(
        b64decode(base_content.content).decode(),
        result,
        base,
        target,
    )

    pr_msg = f""":robot: Release {target}
---
### Description
- New Release: `{target}`
- Based on: `{base}`
- When: `{datetime.now()}`

### Diff
```diff
diff {base_file} {target_file}:
{diff}
```

### Details
_This pull request was generated by [{jobname}]({joburl})_.

Source code for this script can be found [here](https://github.com/equinor/komodo).
"""

    repo.create_git_ref(ref="refs/heads/" + target, sha=from_sha)
    # making a temporary PR in order to squash the commits into one
    tmp_pr = repo.create_pull(
        title=f"Temporary PR {target}",
        body="should not be seen",
        head=tmp_target,
        base=target,
    )
    tmp_pr.merge(
        commit_message=pr_msg,
        commit_title=f"Add release {target}",
        merge_method="squash",
    )
    with contextlib.suppress(github.GithubException):
        tmp_ref.delete()
        # If exception occurs, deletion is automatic

    # done with temporary PR, making the real PR:
    repo.create_pull(
        title=f"Add release {target}",
        body=pr_msg,
        head=target,
        base=git_ref,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy proposals into release and create PR.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "base",
        type=str,
        help=(
            "The name of the release to base on. (E.g. 2021.06.b0). "
            "A corresponding file must exist in releases/matrices"
        ),
    )
    parser.add_argument(
        "target",
        type=str,
        help="The name of the new release file to create. (E.g. 2021.06.b0).",
    )
    parser.add_argument("joburl", help="link to the job that triggered this")
    parser.add_argument("jobname", help="name of the job")
    parser.add_argument("--git-fork", help="git fork", default="equinor")
    parser.add_argument("--git-repo", help="git repo", default="komodo-releases")
    parser.add_argument("--git-ref", help="git ref", default="main")
    return parser.parse_args()


if __name__ == "__main__":
    main()
