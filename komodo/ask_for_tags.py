#!/usr/bin/env python3

import base64
import os
import re
from collections import defaultdict
from textwrap import dedent
from typing import Callable, List, Mapping

import yaml
from github import Github
from github.Commit import Commit
from github.GithubException import GithubException, UnknownObjectException
from github.Repository import Repository

not_in_komodo_releases_project_msg = (
    "We expect this script to be run in the komodo-releases project"
)


def get_packages_that_use_main() -> List[str]:
    bleeding_release_file = "releases/matrices/bleeding.yml"
    duplicate_pkgs = ["everest-models"]  # this is included in the everest repo
    try:
        with open(bleeding_release_file, "r", encoding="utf-8") as bleeding_raw:
            bleeding = yaml.safe_load(bleeding_raw)
    except FileNotFoundError as err:
        raise FileNotFoundError(not_in_komodo_releases_project_msg) from err

    main_pkgs_in_bleeding = [
        pkg.lower()
        for pkg, version in bleeding.items()
        if version == "main" and pkg not in duplicate_pkgs
    ]
    return main_pkgs_in_bleeding


def get_repos(gh_client: Github, packages: List[str]) -> List[Repository]:
    """tries to download repositories based on provided package names, using some
    predefined fork names. throws if repo for a package could not be found / accessed
    """

    DEFAULT_FORK = "equinor"
    ALTERNATE_FORK = "tno-everest"

    repos = []
    for package in packages:
        try:
            repo = gh_client.get_repo(f"{DEFAULT_FORK}/{package}")
        except UnknownObjectException:
            repo = gh_client.get_repo(f"{ALTERNATE_FORK}/{package}")
        repos.append(repo)

    packages_without_repo = [
        pkg for pkg in packages if pkg not in [repo.name.lower() for repo in repos]
    ]
    if packages_without_repo:
        errMsg = (
            "Could not find / access repo for following packages: "
            f"{packages_without_repo}"
        )
        raise RuntimeError(errMsg)
    return repos


def get_latest_commit(repo: Repository) -> Commit:
    DEFAULT_BRANCH = "main"
    ALTERNATE_BRANCH = "master"
    try:
        return repo.get_branch(DEFAULT_BRANCH).commit
    except GithubException:
        return repo.get_branch(ALTERNATE_BRANCH).commit


def get_commit_of_latest_release(repo: Repository) -> Commit:
    last_release = repo.get_latest_release()
    tags = repo.get_tags()
    release_tag = [tag for tag in tags if tag.name == last_release.tag_name][0]
    return release_tag.commit


def find_repos_with_changes_since_last_release(
    repos: List[Repository],
) -> List[Repository]:
    repos_with_changes = []
    for repo in repos:
        last_commit = get_latest_commit(repo)
        release_commit = get_commit_of_latest_release(repo)
        if last_commit != release_commit:
            repos_with_changes.append(repo)
    return repos_with_changes


def get_scout_maintainers(gh_client: Github) -> Mapping[str, str]:
    scout_repo = gh_client.get_repo("equinor/scout")
    projects_file = scout_repo.get_contents("projects.md")
    projects_file_contents = base64.b64decode(projects_file.content).decode()

    def find_all_xs(entries: List[str], xs: List[int]) -> List[int]:
        last_index = xs[-1] if xs else 0
        try:
            find_x = entries.index("X", last_index + 1)
        except ValueError:
            return xs
        xs.append(find_x)
        return find_all_xs(entries, xs)

    table_lines = [
        line
        for line in projects_file_contents.splitlines()
        if line.startswith("|") and line.endswith("|")
    ]
    maintainer_entries = table_lines[0].split("|")
    project_maintainers = defaultdict(list)
    # ignore header and sub header lines in table
    for project_line in table_lines[2:]:
        entries = project_line.split("|")
        package_github_address = re.search(r"\((.*)\)", entries[1]).group(1)
        package_name = package_github_address.split("/")[-1]

        indexes_marking_maintainers = find_all_xs(
            [entry.strip() for entry in entries], []
        )
        for index in indexes_marking_maintainers:
            raw_maintainer_entry = maintainer_entries[index]
            maintainer = re.search(r"\[(.*)\]", raw_maintainer_entry).group(1)
            project_maintainers[package_name].append(maintainer)

    return project_maintainers


def create_maintainer_fetcher(gh_client: Github) -> Callable[[Repository], List[str]]:
    all_scout_maintainers = get_scout_maintainers(gh_client)
    KOMODO_COLLECTION_FILE = "repository.yml"
    try:
        with open(
            KOMODO_COLLECTION_FILE, mode="r", encoding="utf-8"
        ) as komodo_colletion_file:
            komodo_colletion = yaml.safe_load(komodo_colletion_file)
    except FileNotFoundError as err:
        raise FileNotFoundError(not_in_komodo_releases_project_msg) from err

    def get_maintainers(repo: str) -> List[str]:
        scout_maintainers = all_scout_maintainers.get(repo)
        if scout_maintainers:
            return scout_maintainers
        last_version = list(komodo_colletion[repo])[0]
        external_maintainer = komodo_colletion[repo][last_version].get("maintainer")
        if not external_maintainer:
            raise RuntimeError(
                f"Could not find maintainer for `{repo}` in scout projects table "
                f"or in komodo releases {KOMODO_COLLECTION_FILE} file"
            )
        return [external_maintainer]

    return get_maintainers


def build_message_to_maintainers(repos: List[Repository], gh_client: Github) -> str:
    fetch_maintainers = create_maintainer_fetcher(gh_client)
    intro_text = dedent(
        """
        Dear maintainers, I am planning to make a new beta build - I have identified
        packages that have changes since the latest tag was made. if you would like to
        include those changes in this beta build, please create a (beta) tag (for
        whichever commit you want to include) and create an upgrade proposal PR on
        komodo-releases to include the tag
        """
    )
    repo_with_maintainers_line = "\n".join(
        [
            (
                f"[{repo.name}]({repo.url}) - "
                f"{' / '.join(fetch_maintainers(repo.name.lower()))}"
            )
            for repo in repos
        ]
    )
    outro = dedent(
        """
        if you feel that you're not (the sole) responsible for the package i put
        you down for, please let me know who i should ping instead
        (additionally), and i will update the coresponding documentation.

        The reason for this message and building a beta like such is that all komodo
        bleeding tests passed last night :tada:
        """
    )
    return "\n".join([intro_text, repo_with_maintainers_line, outro])


def main():
    github_token = os.getenv("GITHUB_TOKEN", None)
    if github_token is None:
        raise ValueError(
            "Please provide a github access token through the env var `GITHUB_TOKEN`\n"
            "Note that the token should be a personal access token "
            "(not fine-grained),\n configured for SSO with equinor"
        )

    gh_client = Github(login_or_token=github_token)

    packages = get_packages_that_use_main()
    repos = get_repos(gh_client, packages)
    repos_with_changes = find_repos_with_changes_since_last_release(repos)
    if not repos_with_changes:
        print("all releases are up to date!")
        return
    print(
        "repos with changes:\n", "\n".join([repo.name for repo in repos_with_changes])
    )
    message = build_message_to_maintainers(repos_with_changes, gh_client)
    print("here's the message to the maintainers:\n")
    print(message)


if __name__ == "__main__":
    main()
