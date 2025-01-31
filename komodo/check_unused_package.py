#!/usr/bin/env python
import argparse
import os
import sys

import yaml
from typing import Any

from komodo.prettier import load_yaml
from komodo.yaml_file_types import ReleaseFile, RepositoryFile

from .pypi_dependencies import PypiDependencies


def check_for_unused_package(
    release_file: ReleaseFile,
    package_status: dict[str, Any],
    repository: RepositoryFile,
    builtin_python_versions: dict[str, str],
):
    public_and_plugin_packages = [
        (pkg, version)
        for pkg, version in release_file.content.items()
        if package_status[pkg]["visibility"] in ("public", "private-plugin")
    ]
    python_version = release_file.content["python"]
    full_python_version = builtin_python_versions[python_version]

    dependencies = PypiDependencies(
        release_file.content, release_file.content, python_version=full_python_version
    )
    for name, version in release_file.content.items():
        metadata = repository.content.get(name, {}).get(version, {})
        if metadata.get("source") != "pypi":
            dependencies.add_user_specified(name, metadata.get("depends", []))
    unused_private_packages = {
        pkg
        for pkg in release_file.content
        if package_status[pkg]["visibility"] == "private"
    }.difference(dependencies.used_packages(public_and_plugin_packages))
    if unused_private_packages:
        print(
            f"The following {len(unused_private_packages)} private packages are not dependencies of any public or private-plugin packages:"
        )
        print(", ".join(sorted(unused_private_packages)))
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
    with open("builtin_python_versions.yml", encoding="utf-8") as f:
        builtin_python_versions = yaml.safe_load(f)
    package_status = load_yaml(package_status_file)
    check_for_unused_package(
        args.release_file, package_status, args.repo, builtin_python_versions
    )


if __name__ == "__main__":
    main()
