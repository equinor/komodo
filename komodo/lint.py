#!/usr/bin/env python

import argparse
import logging
import sys
import warnings
from collections import namedtuple

from pkg_resources import PkgResourcesDeprecationWarning, parse_version

from komodo.yaml_file_types import KomodoException, ReleaseFile, RepositoryFile

komodo_error = namedtuple(
    "KomodoError",
    ["package", "version", "maintainer", "depends", "err"],
)

report = namedtuple(
    "LintReport",
    ["release_name", "maintainers", "dependencies", "versions"],
)


MISSING_PACKAGE = "missing package"
MISSING_VERSION = "missing version"
MISSING_DEPENDENCY = "missing dependency"
MISSING_MAINTAINER = "missing maintainer"
MISSING_MAKE = "missing make information"
MALFORMED_VERSION = "malformed version"
MAIN_VERSION = "dangerous version (main branch)"
MASTER_VERSION = "dangerous version (master branch)"
FLOAT_VERSION = "dangerous version (float interpretable)"


def _komodo_error(package=None, version=None, maintainer=None, depends=None, err=None):
    return komodo_error(
        package=package,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err,
    )


def lint_version_numbers(package, version, repo):
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


def lint(release_file: ReleaseFile, repository_file: RepositoryFile):
    mns, deps, versions = [], [], []
    for package_name, package_version in release_file.content.items():
        try:
            lint_maintainer = repository_file.lint_maintainer(
                package_name,
                package_version,
            )  # throws komodoexception on missing package or version in repository
            if lint_maintainer:
                mns.append(lint_maintainer)

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
                deps.append(
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
            mns.append(e.error)

    return report(
        release_name=[],
        maintainers=mns,
        dependencies=deps,
        versions=versions,
    )


def get_args():
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


def lint_main():
    args = get_args()
    logging.basicConfig(format="%(message)s", level=args.loglevel)

    try:
        report = lint(args.packagefile, args.repofile)
        mns, deps, versions = report.maintainers, report.dependencies, report.versions
    except ValueError as err:
        sys.exit(str(err))
    print(f"{len(mns)} packages")
    if not any(err.err for err in mns + deps + versions):
        print("No errors found")
        sys.exit(0)

    for err in mns + deps + versions:
        if err.err:
            dep = f": {', '.join(err.depends)}" if err.depends else ""
            print(f"{err.err}{dep}")

    if not any(err.err for err in mns + deps):
        sys.exit(0)  # currently we allow erronous version numbers

    sys.exit("Error in komodo configuration.")


if __name__ == "__main__":
    lint_main()
