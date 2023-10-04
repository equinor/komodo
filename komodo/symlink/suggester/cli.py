#!/usr/bin/env python
import argparse
import logging
import os
import sys
from base64 import b64decode
from datetime import datetime
from typing import Optional

from github import Github
from github.GithubException import UnknownObjectException
from github.Repository import Repository

from komodo.symlink.suggester import configuration

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

PR_TEMPLATE = """:robot: Suggesting updating {mode} to {release} in {sym_file}
---
### Description
- Release: `{release}`
- Link type: `{mode}`
- When: `{now}`

### Details
_This pull request was generated by [{job_name}]({job_url})_.

Source code for this script can be found [here](https://github.com/equinor/komodo/tree/main/komodo/symlink/suggester).
"""  # noqa


def _parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("release", help="e.g. 2019.12.rc0-py38")
    parser.add_argument("mode", help="stable,testing,unstable")
    parser.add_argument("joburl", help="link to the job that triggered this")
    parser.add_argument("jobname", help="name of the job")
    parser.add_argument(
        "--symlink-conf-path",
        help="",
        default="symlink_configuration/symlink_config.json",
    )
    parser.add_argument("--git-fork", help="git fork", default="equinor")
    parser.add_argument("--git-repo", help="git repo", default="komodo-releases")
    parser.add_argument("--git-ref", help="git ref", default="main")
    parser.add_argument(
        "--verbose", "-v", help="Set loglevel to INFO", action="store_true"
    )
    parser.add_argument(
        "--dry-run",
        help="Set dry-run, will do everything except making the PR",
        action="store_true",
    )
    return parser.parse_args()


def _get_repo(token: Optional[str], fork: str, repo: str) -> Repository:
    client = Github(token)
    try:
        return client.get_repo(f"{fork}/{repo}")
    except UnknownObjectException:
        org = client.get_organization(fork)
        return org.get_repo(repo)


def suggest_symlink_configuration(
    args: argparse.Namespace, repo: Repository, dry_run: bool = False
) -> Optional[Repository]:
    """Returns a pull request if the symlink configuration could be updated,
    or None if no update was possible."""
    try:
        sym_conf_content = repo.get_contents(args.symlink_conf_path, ref=args.git_ref)
    except UnknownObjectException:
        sys.exit(f"Filename {args.symlink_conf_path} is not in repo {repo.full_name}")

    try:
        new_symlink_content, updated = configuration.update(
            b64decode(sym_conf_content.content), args.release, args.mode
        )
    except ValueError as exc:
        logger.critical(exc)
        sys.exit(1)

    if not updated:
        logger.info("Nothing to update")
        return None

    target_branch = f"{args.release}/{args.mode}"
    if "azure" in args.symlink_conf_path:
        target_branch += "/azure"

    from_sha = repo.get_branch(args.git_ref).commit.sha

    msg = f"Update {args.mode} symlinks for {args.release}"
    if not dry_run:
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=from_sha)
        repo.update_file(
            args.symlink_conf_path,
            msg,
            new_symlink_content,
            sym_conf_content.sha,
            branch=target_branch,
        )

    body = PR_TEMPLATE.format(
        sym_file=args.symlink_conf_path,
        change=target_branch,
        release=args.release,
        mode=args.mode,
        now=datetime.now(),
        job_url=args.joburl,
        job_name=args.jobname,
    )

    if dry_run:
        print("Dry-run, not making this PR:")
        print(f"title={msg}")
        print(f"body={body}")
        print(f"head_target={target_branch}")
        print(f"base={args.git_ref}")
        return None
    return repo.create_pull(title=msg, body=body, head=target_branch, base=args.git_ref)


def main():
    args = _parse_args()
    repo = _get_repo(os.getenv("GITHUB_TOKEN"), args.git_fork, args.git_repo)

    if args.verbose:
        logger.setLevel(logging.INFO)

    pull = suggest_symlink_configuration(args, repo, dry_run=args.dry_run)
    if pull is None:
        # Warnings should already be logged in this situation
        sys.exit(0)

    print(pull.html_url)


if __name__ == "__main__":
    main()
