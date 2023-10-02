import argparse
import copy
import pathlib
import sys

import requests
import ruamel.yaml
from packaging import version as get_version
from packaging.specifiers import InvalidSpecifier, SpecifierSet

from komodo.package_version import LATEST_PACKAGE_ALIAS, strip_version
from komodo.prettier import write_to_file
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


class YankedException(Exception):
    pass


def yaml_parser():
    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    return yaml


def load_from_file(yaml, fname):
    with open(fname, encoding="utf-8") as fin:
        return yaml.load(fin)


def get_pypi_info(package_names):
    return [
        (
            package,
            requests.get(f"https://pypi.python.org/pypi/{package}/json", timeout=60),
        )
        for package in package_names
    ]


def get_python_requirement(sources: list):
    """Goes through the different sources of the package and returns the first
    python requirement
    :param sources:
    :return: Python requirement or empty string if there is no requirement.
    """
    for source in sources:
        if source.get("yanked", False):
            msg = "Release has been yanked"
            raise YankedException(msg)
        required_python = source.get("requires_python", "")
        if required_python:
            return required_python
    return ""


def compatible_versions(releases: dict, python_version):
    compatible_versions = []
    for version_str, build_info in releases.items():
        try:
            package_version = get_version.parse(version_str)
        except get_version.InvalidVersion:  # presumably unparsable pre-release
            continue
        if package_version.is_prerelease:
            continue
        try:
            required_python = SpecifierSet(get_python_requirement(build_info))
        except YankedException:
            continue
        except InvalidSpecifier:
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
            msg = f"Version: {version} of package: {package} not found in repository"
            raise ValueError(
                msg,
            ) from err
    return pypi_packages


def get_upgrade_proposals_from_pypi(
    releases: dict,
    repository: dict,
    python_version: str,
) -> dict:
    pypi_packages = get_pypi_packages(releases, repository)
    pypi_responses = get_pypi_info(pypi_packages)

    upgrade_proposals_from_pypi = {}

    for package_name, response in pypi_responses:
        komodo_version = get_version.parse(strip_version(releases[package_name]))
        if response.ok:
            pypi_versions = compatible_versions(
                response.json()["releases"],
                python_version,
            )
            pypi_latest_version = max(pypi_versions)
        else:
            msg = f"Response returned non valid return code: {response.reason}"
            raise ValueError(
                msg,
            )
        if pypi_latest_version != komodo_version:
            upgrade_proposals_from_pypi[package_name] = {
                "previous": releases[package_name],
                "suggested": str(pypi_latest_version),
            }

    return upgrade_proposals_from_pypi


def insert_upgrade_proposals(upgrade_proposals, repository, releases):
    for package, version in upgrade_proposals.items():
        suggested_version = version["suggested"]
        if suggested_version not in repository[package]:
            repository[package].update(
                {
                    suggested_version: copy.deepcopy(
                        repository[package][version["previous"]],
                    ),
                },
            )
            repository[package].move_to_end(suggested_version, last=False)
        releases[package] = suggested_version


def run_check_up_to_date(
    release_file,
    repository_file,
    python_version=(
        f"{sys.version_info.major}."
        f"{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    ),
    propose_upgrade=False,
):
    yaml = yaml_parser()
    releases = load_from_file(yaml, release_file)
    repository = load_from_file(yaml, repository_file)
    upgrade_proposals_from_pypi = get_upgrade_proposals_from_pypi(
        releases,
        repository,
        python_version,
    )
    if upgrade_proposals_from_pypi:
        if propose_upgrade:
            insert_upgrade_proposals(upgrade_proposals_from_pypi, repository, releases)
            print(
                "Writing upgrade proposals from pypi, "
                "assuming nothing has changed with dependencies...",
            )
            with open(propose_upgrade, mode="w", encoding="utf-8") as fout:
                yaml.dump(releases, fout)
            write_to_file(repository, repository_file)

        major_upgrades, minor_upgrades, patch_upgrades, other_upgrades = [], [], [], []
        for name, versions in upgrade_proposals_from_pypi.items():
            pypi_latest = get_version.Version(versions["suggested"])
            current_version = get_version.Version(versions["previous"])
            if pypi_latest.major > current_version.major:
                major_upgrades.append(
                    f"{name} not at latest pypi version: {pypi_latest}, "
                    f"is at: {current_version}"
                )
            elif pypi_latest.minor > current_version.minor:
                minor_upgrades.append(
                    f"{name} not at latest pypi version: {pypi_latest}, "
                    f"is at: {current_version}"
                )
            elif pypi_latest.micro > current_version.micro:
                patch_upgrades.append(
                    f"{name} not at latest pypi version: {pypi_latest}, "
                    f"is at: {current_version}"
                )
            else:
                other_upgrades.append(
                    f"{name} not at latest pypi version: {pypi_latest}, "
                    f"is at: {current_version}"
                )
        print(
            "\n".join(
                ["\nMajor upgrades:"]
                + (major_upgrades if major_upgrades else ["None"])
                + ["\nMinor upgrades:"]
                + (minor_upgrades if minor_upgrades else ["None"])
                + ["\nPatch upgrades:"]
                + (patch_upgrades if patch_upgrades else ["None"])
                + ["\nOther upgrades:"]
                + (other_upgrades if other_upgrades else ["None"])
                + ["\n\nFound out of date packages!"]
            )
        )

    else:
        print("All packages up to date!!!")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Checks if pypi packages are up to date.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "release_file",
        type=lambda arg: (
            arg if pathlib.Path(arg).is_file() else parser.error(f"{arg} is not a file")
        ),
        help=(
            "Komodo release file you would like to check dependencies on, "
            "in YAML format."
        ),
    )
    parser.add_argument(
        "repository_file",
        type=lambda arg: (
            arg if pathlib.Path(arg).is_file() else parser.error(f"{arg} is not a file")
        ),
        help=(
            "Komodo repository file where the source of the packages is found, "
            "in YAML format."
        ),
    )
    parser.add_argument(
        "--propose-upgrade",
        default=False,
        help=(
            "If given, will change the repository and release file "
            "using the argument as name of the release file."
        ),
    )
    parser.add_argument(
        "--python-version",
        default=(
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        ),
        help=(
            "Which python version to upgrade to, defaults to the system python. Should"
            " provide it on the form: major.minor.micro, though only: major or:"
            " major.minor is allowed (but might give unexpected results, for example"
            " if a package requires >3.6, py-version 3.6 will not be considered valid)"
        ),
    )

    return parser.parse_args()


def main():
    args = get_args()

    print(f"Checking against python version: {args.python_version}")

    validate_release_file(args.release_file)
    validate_repository_file(args.repository_file)

    run_check_up_to_date(
        args.release_file,
        args.repository_file,
        args.python_version,
        args.propose_upgrade,
    )


def validate_release_file(file_path: str) -> None:
    ReleaseFile()(file_path)


def validate_repository_file(file_path: str) -> None:
    RepositoryFile()(file_path)
