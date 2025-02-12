#!/usr/bin/env python
"""
Checks that for a given release, all private packages (as defined in the visibility
field of the package status file) is the dependency of some public package.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any

import yaml

from komodo.prettier import load_yaml
from komodo.yaml_file_types import ReleaseFile, RepositoryFile

from .pypi_dependencies import PypiDependencies, version_list_to_requirements


@dataclass
class CheckResult:
    message: str
    exitcode: int


class NoSuchPackageStatus(ValueError):
    """Raised when a package is not present in the package status file"""

    exit_code = 2


class NoSuchRepository(ValueError):
    """Raised when a package is not present in the repository file"""

    exit_code = 3


def check_for_unused_package(
    release_file: ReleaseFile,
    package_status: dict[str, Any],
    repository: RepositoryFile,
    builtin_python_versions: dict[str, str],
) -> CheckResult:
    def get_visibility(pkg):
        try:
            status = package_status[pkg]
        except KeyError as err:
            raise NoSuchPackageStatus(
                f"Could not find {pkg} in the package status file"
            ) from err
        try:
            return status["visibility"]
        except KeyError as err:
            raise NoSuchPackageStatus(
                f"{pkg} does not have visibility field in package status file"
            ) from err

    try:
        private_packages = {
            pkg for pkg in release_file.content if get_visibility(pkg) == "private"
        }
        public_packages = version_list_to_requirements(
            (pkg, version)
            for pkg, version in release_file.content.items()
            if get_visibility(pkg) in ("public", "private-plugin")
        )
        dependencies = _extract_dependencies(
            release_file,
            repository,
            builtin_python_versions[release_file.content["python"]],
        )
    except (NoSuchPackageStatus, NoSuchRepository) as err:
        return CheckResult(message=str(err), exitcode=err.exit_code)

    used_packages = dependencies.used_packages(public_packages)

    if unused_private_packages := private_packages.difference(used_packages):
        return CheckResult(
            message=f"The following {len(unused_private_packages)} private packages are"
            " not dependencies of any public or private-plugin packages:"
            + ", ".join(sorted(unused_private_packages))
            + "If you have added or removed any packages check that the dependencies"
            " in repository.yml are correct.",
            exitcode=1,
        )
    else:
        return CheckResult(message="Everything seems fine.", exitcode=0)


def _extract_dependencies(release_file, repository, full_python_version):
    dependencies = PypiDependencies(
        release_file.content,
        python_version=full_python_version,
    )
    for name, version in release_file.content.items():
        try:
            metadata = repository.content[name][version]
        except KeyError as err:
            raise NoSuchRepository(
                f"Could not find package-version: {name}:{version} in the repository file"
            ) from err
        if metadata.get("source") != "pypi":
            dependencies.add_user_specified(name, metadata.get("depends", []))
    return dependencies


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
        help="Repository file wich lists where to get the package from.",
    )

    args = parser.parse_args()
    with open("builtin_python_versions.yml", encoding="utf-8") as f:
        builtin_python_versions = yaml.safe_load(f)
    package_status = load_yaml(args.status_file)
    result = check_for_unused_package(
        args.release_file, package_status, args.repo, builtin_python_versions
    )
    print(result.message)
    exit(result.exitcode)


if __name__ == "__main__":
    main()
