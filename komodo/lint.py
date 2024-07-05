#!/usr/bin/env python

import argparse
import logging
import sys
import warnings
from collections import namedtuple

import yaml
from packaging.version import parse

from .pypi_dependencies import PypiDependencies
from .yaml_file_types import KomodoException, ReleaseFile, RepositoryFile

KomodoError = namedtuple(
    "KomodoError",
    ["package", "version", "maintainer", "depends", "err"],
)

Report = namedtuple(
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
    return KomodoError(
        package=package,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err,
    )


def lint_version_numbers(package, version, repo):
    package_release = repo[package][version]
    maintainer = package_release.get("maintainer", MISSING_MAINTAINER)

    try:
        logging.info(f"Using {package} {version}")
        if "main" in version:
            return _komodo_error(package, version, maintainer, err=MAIN_VERSION)
        if "master" in version:
            return _komodo_error(package, version, maintainer, err=MASTER_VERSION)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            parsed_version = parse(version)
            # A warning coincides with finding "Legacy" in repr(v)
        if "Legacy" in repr(
            parsed_version
        ):  # don't know if possible to check otherwise
            return _komodo_error(package, version, maintainer)
    except:  # pylint: disable=bare-except  # noqa
        # Log any exception:
        return _komodo_error(package, version, maintainer)
    return None


def lint(
    release_file: ReleaseFile,
    repository_file: RepositoryFile,
    check_dependencies: bool = False,
) -> Report:
    maintainers, versions = [], []
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
        except KomodoException as komodo_exception:
            maintainers.append(komodo_exception.error)

    if check_dependencies:
        pypi_dependencies = {
            name: version
            for name, version in release_file.content.items()
            if repository_file.content.get(name, {}).get(version, {}).get("source")
            == "pypi"
        }

        python_version = release_file.content["python"]
        with open("builtin_python_versions.yml", encoding="utf-8") as f:
            full_python_version = yaml.safe_load(f)[python_version]

        dependencies = PypiDependencies(
            pypi_dependencies, python_version=full_python_version
        )
        for name, version in release_file.content.items():
            if (
                repository_file.content.get(name, {}).get(version, {}).get("source")
                != "pypi"
            ):
                if (
                    name not in repository_file.content
                    or version not in repository_file.content[name]
                ):
                    raise ValueError(
                        f"Missing package in repository file: {name}=={version}"
                    )
                depends = repository_file.content[name][version].get("depends", [])
                if depends:
                    dependencies.add_user_specified(
                        name, repository_file.content[name][version]["depends"]
                    )

        failed_requirements = dependencies.failed_requirements()
        if failed_requirements:
            deps = [
                _komodo_error(
                    err="Failed requirements ",
                    depends=[str(r) for r in failed_requirements],
                )
            ]
        else:
            deps = []
        dependencies.dump_cache()
    else:
        deps = []

    return Report(
        release_name=[],
        maintainers=maintainers,
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
    parser.add_argument(
        "--check-pypi-dependencies",
        dest="check_pypi_dependencies",
        help="Checks package metadata",
        action="store_true",
        default=False,
    )
    return parser.parse_args()


def lint_main():
    args = get_args()
    logging.basicConfig(format="%(message)s", level=args.loglevel)

    report = lint(
        args.packagefile, args.repofile, check_dependencies=args.check_pypi_dependencies
    )
    maintainers, deps, versions = (
        report.maintainers,
        report.dependencies,
        report.versions,
    )
    print(f"{len(maintainers)} packages")
    if not any(err.err for err in maintainers + deps + versions):
        print("No errors found")
        sys.exit(0)

    for err in maintainers + deps + versions:
        if err.err:
            print(f"{err.err}")
            if err.depends:
                print("\n  ".join(err.depends))

    if not any(err.err for err in maintainers + deps):
        sys.exit(0)  # currently we allow erronous version numbers

    sys.exit("Error in komodo configuration.")


if __name__ == "__main__":
    lint_main()
