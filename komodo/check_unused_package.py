#!/usr/bin/env python

import argparse
import os
import sys

from komodo.build import full_dfs
from komodo.prettier import load_yaml
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def check_for_unused_package(
    release_file: ReleaseFile, package_status_file: str, repository: RepositoryFile
):
    package_status = load_yaml(package_status_file)
    private_packages = [
        pkg
        for pkg in release_file.content
        if package_status[pkg]["visibility"] == "private"
    ]
    public_and_plugin_packages = [
        pkg
        for pkg in release_file.content
        if package_status[pkg]["visibility"] in ("public", "private-plugin")
    ]
    public_and_plugin_dependencies = full_dfs(
        release_file.content,
        repository.content,
        public_and_plugin_packages,
    )
    diff_packages = set(private_packages).difference(
        set(public_and_plugin_dependencies)
    )
    if diff_packages:
        print(
            f"The following {len(diff_packages)} private packages are not dependencies of any public or private-plugin packages:"
        )
        print(", ".join(sorted(list(diff_packages))))
        print(
            "If you have added or removed any packages check that the dependencies in repository.yml are correct."
        )
        sys.exit(1)
    else:
        print("Everything seems fine.")


def main():
    parser = argparse.ArgumentParser(
        description=("Reports packages that have status private and are not in use."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "release_file",
        type=ReleaseFile(),
        help="File with packages you want to check for unused private packages.",
    )
    parser.add_argument(
        "status_file",
        type=lambda arg: (
            arg if os.path.isfile(arg) else parser.error(f"{arg} is not a file")
        ),
        help="File which lists the status of the packages.",
    )
    parser.add_argument(
        "repo",
        type=RepositoryFile(),
        help="Repository file with all packages listed with dependencies.",
    )

    args = parser.parse_args()
    check_for_unused_package(args.release_file, args.status_file, args.repo)


if __name__ == "__main__":
    main()
