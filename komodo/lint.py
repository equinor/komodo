#!/usr/bin/env python

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from dataclasses import dataclass
from typing import Any, Mapping, MutableSequence, Optional, Sequence, Union

from pkg_resources import PkgResourcesDeprecationWarning, parse_version

from komodo.yaml_file_types import KomodoException, ReleaseFile, RepositoryFile


@dataclass
class komodo_error:
    package: Optional[str] = None
    version: Optional[str] = None
    maintainer: Optional[str] = None
    depends: Optional[Sequence[str]] = None
    err: Union[None, KomodoException, str] = None


@dataclass
class report:
    release_name: Sequence[str]
    maintainers: Sequence[Any]
    dependencies: Sequence[Any]
    versions: Sequence[Any]


MISSING_PACKAGE = "missing package"
MISSING_VERSION = "missing version"
MISSING_DEPENDENCY = "missing dependency"
MISSING_MAINTAINER = "missing maintainer"
MISSING_MAKE = "missing make information"
MALFORMED_VERSION = "malformed version"
MAIN_VERSION = "dangerous version (main branch)"
MASTER_VERSION = "dangerous version (master branch)"
FLOAT_VERSION = "dangerous version (float interpretable)"


def _komodo_error(
    package: Optional[str] = None,
    version: Optional[str] = None,
    maintainer: Optional[str] = None,
    depends: Optional[Sequence[str]] = None,
    err: Union[None, KomodoException, str] = None,
) -> komodo_error:
    return komodo_error(
        package=package,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err,
    )


def lint_version_numbers(
    package: str, version: str, repo: Mapping[str, Any]
) -> Optional[komodo_error]:
    pv = repo[package][version]
    maintainer = pv.get("maintainer", MISSING_MAINTAINER)

    try:
        logging.info(f"Using {package} {version}")
        if "main" in version:
            return _komodo_error(package, version, maintainer, err=MAIN_VERSION)
        if "master" in version:
            return _komodo_error(package, version, maintainer, err=MASTER_VERSION)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PkgResourcesDeprecationWarning)
            v = parse_version(version)
            # A warning coincides with finding "Legacy" in repr(v)
        if "Legacy" in repr(v):  # don't know if possible to check otherwise
            return _komodo_error(package, version, maintainer)
    except:  # pylint: disable=bare-except  # noqa
        # Log any exception:
        return _komodo_error(package, version, maintainer)
    return None


def lint(release_file: ReleaseFile, repository_file: RepositoryFile) -> report:
    maintainers: MutableSequence[Any] = []
    dependencies: MutableSequence[Any] = []
    versions: MutableSequence[Any] = []
    for package_name, package_version in release_file.content.items():
        try:
            lint_maintainer = repository_file.lint_maintainer(
                package_name,
                package_version,
            )  # throws komodoexception on missing package or version in repository
            if lint_maintainer:
                maintainers.append(lint_maintainer)

            lint_version_number = lint_version_numbers(
                package_name,
                package_version,
                repository_file.content,
            )
            if lint_version_number:
                versions.append(lint_version_number)
            missing = []
            repository_file_package_version_data = repository_file.content.get(
                package_name,
            ).get(package_version)
            for dependency in repository_file_package_version_data.get("depends", []):
                if dependency not in release_file.content:
                    missing.append(dependency)
            if missing:
                dependencies.append(
                    _komodo_error(
                        package=package_name,
                        version=package_version,
                        depends=missing,
                        err=(
                            f"{MISSING_DEPENDENCY} for {package_name} {package_version}"
                        ),
                    ),
                )
        except KomodoException as e:
            maintainers.append(e.error)

    return report(
        release_name=[],
        maintainers=maintainers,
        dependencies=dependencies,
        versions=versions,
    )


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint komodo setup.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "packagefile",
        type=ReleaseFile(),
        help="A Komodo release file mapping package name to version, in YAML format.",
    )
    parser.add_argument(
        "repofile",
        type=RepositoryFile(),
        help="A Komodo repository file, in YAML format.",
    )
    parser.add_argument(
        "--verbose",
        help="Massive amount of outputs.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )
    return parser.parse_args()


def lint_main() -> None:
    args = get_args()
    logging.basicConfig(format="%(message)s", level=args.loglevel)

    try:
        report = lint(args.packagefile, args.repofile)
    except ValueError as err:
        sys.exit(str(err))
    print("%d packages" % len(report.maintainers))
    errors = [*report.maintainers, *report.dependencies, *report.versions]
    if not any(err.err for err in errors):
        print("No errors found")
        sys.exit(0)

    for error in errors:
        if error.err:
            dep = ": %s" % ", ".join(error.depends) if error.depends else ""
            print(f"{error.err}{dep}")

    if not any(err.err for err in (*report.maintainers, *report.dependencies)):
        sys.exit(0)  # currently we allow erronous version numbers

    sys.exit("Error in komodo configuration.")


if __name__ == "__main__":
    lint_main()
