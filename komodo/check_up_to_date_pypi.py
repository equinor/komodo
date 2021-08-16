import copy
import sys
import pathlib

from packaging import version as get_version
from packaging.specifiers import SpecifierSet
import requests
import ruamel.yaml
import argparse
from komodo.package_version import LATEST_PACKAGE_ALIAS, strip_version
from komodo.prettier import write_to_file


class YankedException(Exception):
    pass


def yaml_parser():
    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    return yaml


def load_from_file(yaml, fname):
    with open(fname, "r") as fin:
        result = yaml.load(fin)
    return result


def get_pypi_info(package_names):
    return [
        (package, requests.get(f"https://pypi.python.org/pypi/{package}/json"))
        for package in package_names
    ]


def get_python_requirement(sources: list):
    """
    Goes through the different sources of the package and returns the first
    python requirement
    :param sources:
    :return: Python requirement or empty string if there is no requirement
    """
    for source in sources:
        if source.get("yanked", False):
            raise YankedException("Release has been yanked")
        required_python = source.get("requires_python", "")
        if required_python:
            return required_python
    return ""


def compatible_versions(releases: dict, python_version):
    compatible_versions = []
    for version_str, build_info in releases.items():
        package_version = get_version.parse(version_str)
        if package_version.is_prerelease:
            continue
        try:
            required_python = SpecifierSet(get_python_requirement(build_info))
        except YankedException:
            continue
        if python_version in required_python:
            compatible_versions.append(package_version)
    return compatible_versions


def get_pypi_packages(release: dict, repository: dict) -> list:
    pypi_packages = []
    for package, version in release.items():
        if LATEST_PACKAGE_ALIAS in strip_version(version):
            continue
        try:
            if repository[package][version].get("source", None) == "pypi":
                pypi_packages.append(package)
        except KeyError as err:
            raise ValueError(
                f"Version: {version} of package: {package} not found in repository"
            ) from err
    return pypi_packages


def get_upgrade_proposal(releases: dict, repository: dict, python_version: str) -> dict:

    pypi_packages = get_pypi_packages(releases, repository)
    pypi_response = get_pypi_info(pypi_packages)

    upgrade_proposals = {}
    for name, response in pypi_response:
        komodo_version = get_version.parse(strip_version(releases[name]))
        if response.ok:
            pypi_versions = compatible_versions(
                response.json()["releases"], python_version
            )
            pypi_latest_version = max(pypi_versions)
        else:
            raise ValueError(
                f"Response returned non valid return code: {response.reason}"
            )
        if pypi_latest_version != komodo_version:
            upgrade_proposals[name] = {
                "previous": releases[name],
                "suggested": str(pypi_latest_version),
            }

    return upgrade_proposals


def insert_upgrade_proposals(upgrade_proposals, repository, releases):
    for package, version in upgrade_proposals.items():
        suggested_version = version["suggested"]
        if suggested_version not in repository[package]:
            repository[package].update(
                {
                    suggested_version: copy.deepcopy(
                        repository[package][version["previous"]]
                    )
                }
            )
            repository[package].move_to_end(suggested_version, last=False)
        releases[package] = suggested_version


def main():
    parser = argparse.ArgumentParser(
        description="Checks if pypi packages are up to date"
    )
    parser.add_argument(
        "release_file",
        type=lambda arg: arg
        if pathlib.Path(arg).is_file()
        else parser.error("{} is not a file".format(arg)),
        help="Release file you would like to check dependencies on.",
    )
    parser.add_argument(
        "repository_file",
        type=lambda arg: arg
        if pathlib.Path(arg).is_file()
        else parser.error("{} is not a file".format(arg)),
        help="Repository file where the source of the packages is found",
    )
    parser.add_argument(
        "--propose-upgrade",
        default=False,
        help="If given, will change the repository and release file "
        "using the argument as name of the release file",
    )
    parser.add_argument(
        "--python-version",
        default=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        help="Which python version to upgrade to, defaults to the system python. "
        "Should provide it on the form: major.minor.micro, though only: major or: "
        "major.minor is allowed (but might give unexpected results, for example if "
        "a package requires >3.6, py-version 3.6 will not be considered valid)",
    )

    args = parser.parse_args()
    print(f"Checking against python version: {args.python_version}")
    yaml = yaml_parser()
    releases = load_from_file(yaml, args.release_file)
    repository = load_from_file(yaml, args.repository_file)

    upgrade_proposals = get_upgrade_proposal(releases, repository, args.python_version,)

    if upgrade_proposals:
        if args.propose_upgrade:
            insert_upgrade_proposals(upgrade_proposals, repository, releases)
            print(
                "Writing upgrade proposals, assuming nothing has changed with dependencies..."
            )
            with open(args.propose_upgrade, "w") as fout:
                yaml.dump(releases, fout)
            write_to_file(repository, args.repository_file)

        errors = []
        for name, versions in upgrade_proposals.items():
            pypi_latest = versions["suggested"]
            current_version = versions["previous"]
            errors.append(
                f"{name} not at latest pypi version: {pypi_latest}, is at: {current_version}"
            )
        sys.exit("\n".join(errors) + "\nFound out of date packages!")

    else:
        print("All packages up to date!!!")
