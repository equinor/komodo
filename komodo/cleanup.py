#!/usr/bin/env python

import sys

from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def cleanup(repository_file_path: str, release_files_path: list[str]):
    repository_file = RepositoryFile()(repository_file_path)
    repository = repository_file.content

    releases = []
    for file_name in release_files_path:
        release_file = ReleaseFile()(file_name)
        releases.append(release_file.content)

    registered_package_version_combinations = [
        (package, version) for package in repository for version in repository[package]
    ]

    seen_package_version_combinations = set()
    for release in releases:
        for package_name, package_version in release.items():
            seen_package_version_combinations.add((package_name, package_version))

    seen_all = True
    for ver in registered_package_version_combinations:
        if ver not in seen_package_version_combinations:
            if seen_all:
                print("unused:")
                seen_all = False
            print(f"  - {ver[0]}: {ver[1]}")
    if seen_all:
        print("ok")


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: komodo.cleanup repository.yml rel1.yml rel2.yml ... reln.yml")

    repository = sys.argv[1]
    releases = sys.argv[2:]
    cleanup(repository, releases)


if __name__ == "__main__":
    main()
