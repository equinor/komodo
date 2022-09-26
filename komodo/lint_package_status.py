#!/usr/bin/env python

import argparse

from komodo.yaml_file_type import YamlFile

VALID_VISIBILITY = ["public", "private"]
VALID_IMPORTANCE = ["low", "medium", "high"]
VALID_MATURITY = ["experimental", "stable", "deprecated"]


def run(package_status, repository):
    package_status_set = set(package_status.keys())
    repository_set = set(repository.keys())
    if package_status_set.difference(repository_set):
        raise SystemExit(
            "The following packages are specified in the "
            "package status file, but not in the repository file: {}".format(
                list(package_status_set.difference(repository_set))
            )
        )
    if repository_set.difference(package_status_set):
        raise SystemExit(
            "The following packages are specified in the "
            "repository file, but not in the package status file: {}".format(
                list(repository_set.difference(package_status_set))
            )
        )

    errors = []
    for package, status in package_status.items():
        if status.get("visibility") not in VALID_VISIBILITY:
            errors.append(
                (package, "Malformed visibility: {}".format(status.get("visibility")))
            )
            continue

        visibility = status["visibility"]
        if visibility == "public":
            if status.get("maturity") not in VALID_MATURITY:
                errors.append(
                    (package, "Malformed maturity: {}".format(status.get("maturity")))
                )
            if status.get("importance") not in VALID_IMPORTANCE:
                errors.append(
                    (
                        package,
                        "Malformed importance: {}".format(status.get("importance")),
                    )
                )
    if errors:
        raise SystemExit(
            "\n".join(["{}: {}".format(package, msg) for package, msg in errors])
        )


def get_parser():
    parser = argparse.ArgumentParser(description=("Lint the package status file."))
    parser.add_argument(
        "package_status",
        type=YamlFile(),
        help="File with all package statuses.",
    )
    parser.add_argument(
        "repository",
        type=YamlFile(),
        help="Repository file with all packages listed with dependencies.",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    run(args.package_status, args.repository)
    print("Package status file is valid!")


if __name__ == "__main__":
    main()
