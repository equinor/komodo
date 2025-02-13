#!/usr/bin/env python

import argparse
import os
import re
from typing import Dict, List, Optional, Sequence, Union

import yaml

from komodo.matrix import format_release, get_matrix
from komodo.prettier import load_yaml, write_to_file


def _pick_package_versions_for_release(
    packages: dict,
    rhel_ver: str,
    py_ver: str,
    other_ver: Optional[str] = None,
) -> dict:
    """Consolidate the packages for a given combination of rhel and python version
    into a dictionary.
    """
    release_dict = {}
    for pkg_name, versions in packages.items():
        version = None
        try:
            _check_version_exists_for_coordinates(versions, rhel_ver, py_ver, other_ver)
        except KeyError as err:
            error_msg = f"{err!s}. Failed for {pkg_name}."
            raise KeyError(error_msg) from None
        if isinstance(versions, dict):
            if rhel_ver in versions:
                version = versions[rhel_ver][py_ver]
            elif py_ver in versions:
                version = versions[py_ver]

            if other_ver:
                if other_ver in versions:
                    version = versions[other_ver]
                elif other_ver and other_ver in version:
                    version = version[other_ver]
        else:
            version = versions
        if version:
            release_dict[pkg_name] = version
    return release_dict


def _check_version_exists_for_coordinates(
    pkg_versions: Union[dict, str],
    rhel_coordinate: str,
    py_coordinate: str,
    other_coordinate: Optional[str],
) -> None:
    """Check the coordinates `rhel_ver` and `py_ver` input as arguments to
    build a release against the release matrix file. Raise exceptions if
    coordinates not found.
    pkg_versions can take various levels as the examples show:
        {
            rhel7: # first_level
                py36: 1.1.1, # second_level
                py38: 2.1.1,
            rhel8: # first_level
                py36: 3.1.1, # second_level
                py38: 4.1.1,
        }
        or:
        {
            py36: 1.1.1, # first level
            py38: 2.1.1,
        }
        or:
        {1.1.1}.
        or:
        {
            py36: 1.1.1, # first level
                numpy1: 1.2.6
                numpy2: 2.2.1
            py38: 2.1.1,
                numpy1: 1.2.6
                numpy2: 2.2.1
        }
        or:
        {
            numpy2: 2.2.1
            numpy1: 1.2.6
        }
    """
    if isinstance(pkg_versions, str):
        return None
    first_level_versions = list(pkg_versions)

    def verify_coordinate_in_list(
        coordinate: str, all_coordinates: Sequence[str], seq: Sequence[str]
    ) -> None:
        if not coordinate in seq:
            raise KeyError(
                f"Matrix coordinate {coordinate}, part of {all_coordinates}, not found in {seq}"
            )

    all_coords = [rhel_coordinate, py_coordinate, other_coordinate]

    if "rhel" in first_level_versions[0]:
        verify_coordinate_in_list(rhel_coordinate, all_coords, first_level_versions)
        second_level_versions = list(pkg_versions[rhel_coordinate])
        verify_coordinate_in_list(py_coordinate, all_coords, second_level_versions)

        if other_coordinate:
            third_level_versions = list(pkg_versions[rhel_coordinate][py_coordinate])
            verify_coordinate_in_list(
                other_coordinate, all_coords, third_level_versions
            )

    elif re.match(r"py\d{2,3}", first_level_versions[0]):
        verify_coordinate_in_list(py_coordinate, all_coords, first_level_versions)

        if other_coordinate:
            second_level_versions = list(pkg_versions[py_coordinate])
            verify_coordinate_in_list(
                other_coordinate, all_coords, second_level_versions
            )

    elif other_coordinate:
        verify_coordinate_in_list(other_coordinate, all_coords, first_level_versions)

    else:
        msg = """Invalid package versioning structure."""
        raise KeyError(msg)
    return None


def transpile_releases(matrix_file: str, output_folder: str, matrix: dict) -> None:
    """Transpile a matrix file possibly containing different os and framework
    versions (e.g. rhel6 and rhel7, py3.6 and py3.8).
    Write one dimension file for each element in the matrix
    (e.g. rhel7 and py3.8, rhel6 and py3.6).
    """
    if not isinstance(matrix, dict):
        raise TypeError("Matrix coordinates must be a dictionary")

    rhel_versions = matrix.get("rhel", "8")
    python_versions = matrix.get("py", "311")
    other_versions = None

    for k, v in matrix.items():  # find first item not rhel or py
        if k not in ["rhel", "py"]:
            other_versions = {k: v}
            break

    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")

    for rhel_ver, py_ver, other_ver in get_matrix(
        rhel_versions, python_versions, other_versions
    ):
        release_dict = _pick_package_versions_for_release(
            release_matrix,
            rhel_ver,
            py_ver,
            other_ver,
        )
        filename = f"{format_release(release_base, rhel_ver, py_ver)}"
        if other_versions:
            filename = filename + f"-{other_ver}"
        filename = filename + ".yml"
        write_to_file(release_dict, os.path.join(output_folder, filename))


def transpile_releases_for_pip(
    matrix_file: str,
    output_folder: str,
    repository_file: str,
    matrix: dict,
) -> None:
    if not isinstance(matrix, dict):
        raise TypeError("Matrix coordinates must be a dictionary")

    rhel_versions = matrix.get("rhel", "8")
    python_versions = matrix.get("py", "311")
    other_versions = None

    for k, v in matrix.items():  # find first item not rhel or py
        if k not in ["rhel", "py"]:
            other_versions = {k: v}
            break

    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")
    repository = load_yaml(repository_file)
    for rhel_ver, py_ver, other_ver in get_matrix(
        rhel_versions, python_versions, other_versions
    ):
        release_dict = _pick_package_versions_for_release(
            release_matrix,
            rhel_ver,
            py_ver,
            other_ver,
        )
        pip_packages = [
            f"{pkg}=={version}"
            for pkg, version in release_dict.items()
            if repository[pkg][version].get("make") == "pip"
        ]
        filename = f"{format_release(release_base, rhel_ver, py_ver, other_ver)}.req"
        with open(
            os.path.join(output_folder, filename),
            mode="w",
            encoding="utf-8",
        ) as filehandler:
            filehandler.write("\n".join(pip_packages))


def detect_custom_coordinates(matrix_file: str) -> Dict[str, List[str]]:
    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")

    def traverse_for_custom_coordinates(coords: Dict[str, List[str]]):
        def split_text_and_number(s):
            parts = re.findall(r"(\D+)(\d+)", s)
            return parts[0] if parts else (s, "")

        detected_coordinates = {}

        for val in coords.values():
            if isinstance(val, dict):
                for k, v in val.items():
                    if not re.search(r"rhel", k) and not re.match(r"^py", k):
                        package, version = split_text_and_number(k)

                        if (
                            package in detected_coordinates
                            and version not in detected_coordinates[package]
                        ):
                            detected_coordinates[package].append(version)
                        else:
                            detected_coordinates = {package: [version]}

                    if isinstance(v, dict):
                        detected_coordinates.update(traverse_for_custom_coordinates(v))

        return detected_coordinates

    return traverse_for_custom_coordinates(release_matrix)


def transpile(args):
    if args.auto_custom_coordinates:
        args.matrix_coordinates.update(detect_custom_coordinates(args.matrix_file))

    transpile_releases(args.matrix_file, args.output_folder, args.matrix_coordinates)


def transpile_for_pip(args: Dict):
    if args.auto_custom_coordinates:
        args.matrix_coordinates.update(detect_custom_coordinates(args.matrix_file))

    transpile_releases_for_pip(
        args.matrix_file,
        args.output_folder,
        args.repo,
        args.matrix_coordinates,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Build release files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        description="Transpile - generate release files",
        help="Available sub commands",
        dest="mode",
    )
    subparsers.required = True

    transpile_parser = subparsers.add_parser(
        "transpile",
        description="Transpile a matrix file into separate release files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    transpile_parser.set_defaults(func=transpile)
    transpile_parser.add_argument(
        "--matrix-file",
        required=True,
        type=valid_file,
        help="Yaml file describing the release matrix",
    )
    transpile_parser.add_argument(
        "--output-folder",
        required=True,
        type=dir_path,
        help="Folder to output new release files",
    )
    transpile_parser.add_argument(
        "--matrix-coordinates",
        help="Matrix to be transpiled, expected yaml format string.",
        type=yaml.safe_load,
        required=False,
        default="{rhel: ['8'], py: ['3.11']}",
    )
    transpile_parser.add_argument(
        "--auto-custom-coordinates",
        help="Deduce custom coordinates from yaml input file",
        action="store_true",
        required=False,
    )

    transpile_for_pip_parser = subparsers.add_parser(
        "transpile-for-pip",
        description="transpile a matrix file into separate pip requirement files.",
    )
    transpile_for_pip_parser.set_defaults(func=transpile_for_pip)
    transpile_for_pip_parser.add_argument(
        "--matrix-file",
        required=True,
        help="Yaml file describing the release matrix",
    )
    transpile_for_pip_parser.add_argument(
        "--repo",
        required=True,
        help="A Komodo repository file, in YAML format.",
    )
    transpile_for_pip_parser.add_argument(
        "--output-folder",
        required=True,
        help="Folder to output new release files",
    )
    transpile_for_pip_parser.add_argument(
        "--matrix-coordinates",
        help="Matrix to be transpiled, expected yaml format string.",
        type=yaml.safe_load,
        required=False,
        default="{rhel: ['8'], py: ['3.11']}",
    )
    transpile_for_pip_parser.add_argument(
        "--auto-custom-coordinates",
        help="Deduce custom coordinates from yaml input file",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()
    args.func(args)


def valid_file(path: str) -> str:
    if os.path.isfile(path):
        return path
    raise FileNotFoundError(path)


def dir_path(should_be_valid_path: str) -> str:
    if os.path.isdir(should_be_valid_path):
        return should_be_valid_path
    raise NotADirectoryError(should_be_valid_path)


if __name__ == "__main__":
    main()
