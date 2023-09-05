#!/usr/bin/env python

import argparse

from komodo.yaml_file_types import PackageStatusFile, RepositoryFile


def run(package_status: PackageStatusFile, repository: RepositoryFile):
    package_status_set = set(package_status.content.keys())
    repository_set = set(repository.content.keys())

    compare_sets(
        package_status_set,
        repository_set,
        message=(
            "The following packages are specified in the package status file but not"
            " in the repository file: "
        ),
    )

    compare_sets(
        repository_set,
        package_status_set,
        message=(
            "The following packages are specified in the repository file, but not in"
            " the package status file: "
        ),
    )


def compare_sets(set_a: set, set_b: set, message: str) -> None:
    if set_a.difference(set_b):
        raise SystemExit(message + str(list(set_a.difference(set_b))))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Lint the package status file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "package_status",
        type=PackageStatusFile(),
        help="File with all package statuses.",
    )
    parser.add_argument(
        "repository",
        type=RepositoryFile(),
        help=(
            "Komodo repository file with all packages listed with dependencies, "
            "in YAML format."
        ),
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    run(args.package_status, args.repository)
    print("Package status file is valid!")


if __name__ == "__main__":
    main()
