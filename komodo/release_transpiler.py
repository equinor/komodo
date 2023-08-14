#!/usr/bin/env python

import argparse
import itertools
import os
import re
from pathlib import Path
from typing import Optional, Sequence

import yaml

from komodo.matrix import format_release, get_matrix
from komodo.prettier import load_yaml, write_to_file


def build_matrix_file(
    release_base: str,
    release_folder: str,
    builtins: dict,
    py_coords: Optional[Sequence[str]],
) -> None:
    """Combine release files from the release_folder into one single matrix_file."""
    files = {}
    if py_coords is None:
        py_keys = get_py_coords(release_base, release_folder)
    else:
        py_keys = [f"py{py_version.replace('.', '')}" for py_version in py_coords]

    for key in py_keys:
        files[key] = load_yaml(f"{release_folder}/{release_base}-{key}.yml")

    all_packages = set(
        itertools.chain.from_iterable(files[key].keys() for key in files)
    )
    compiled = {}

    for package in all_packages:
        if package in builtins:
            compiled[package] = builtins[package]
            continue

        if len({files[key].get(package) for key in files}) == 1:
            compiled[package] = next(iter(files.values()))[package]
        else:
            compiled[package] = {key: files[key].get(package) for key in py_keys}

    write_to_file(compiled, f"{release_base}.yml", False)


def get_py_coords(release_base: str, release_folder: str) -> Sequence[str]:
    """Get python versions of release files inside a given release_folder."""
    filenames_with_prefix = sorted(
        [
            filename
            for filename in os.listdir(release_folder)
            if filename.startswith(release_base)
        ]
    )
    len_release_base = len(release_base + "-")
    irrelevant_suffix_length = len(".yml")
    py_coords = [
        filename[len_release_base:-irrelevant_suffix_length]
        for filename in filenames_with_prefix
    ]
    return py_coords


def _pick_package_versions_for_release(
    packages: dict, rhel_ver: str, py_ver: str
) -> dict:
    """Consolidate the packages for a given combination of rhel and python version
    into a dictionary."""
    release_dict = {}
    for pkg_name, versions in packages.items():
        try:
            _check_version_exists_for_coordinates(versions, rhel_ver, py_ver)
        except KeyError as err:
            error_msg = f"{str(err)}. Failed for {pkg_name}."
            raise KeyError(error_msg)

        if rhel_ver in versions:
            version = versions[rhel_ver][py_ver]
        elif py_ver in versions:
            version = versions[py_ver]
        else:
            version = versions

        if version:
            release_dict[pkg_name] = version
    return release_dict


def _check_version_exists_for_coordinates(
    pkg_versions: dict, rhel_coordinate: str, py_coordinate: str
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
        {1.1.1}

    """
    first_level_versions = []
    for version in pkg_versions:
        first_level_versions.append(version)
    if "rhel" in first_level_versions[0]:
        # Both rhel and python versions can have different versions
        if rhel_coordinate not in first_level_versions:
            raise KeyError(f"Rhel version {rhel_coordinate} not found.")
        second_level_versions = []
        for version_py in pkg_versions[rhel_coordinate]:
            second_level_versions.append(version_py)
        if py_coordinate not in second_level_versions:
            raise KeyError(
                f"Python version {py_coordinate} not found for "
                f"rhel version {rhel_coordinate}."
            )
    elif "py" in first_level_versions[0]:
        # Only python has different versions
        if py_coordinate not in first_level_versions:
            raise KeyError(f"Python version {py_coordinate} not found.")


def transpile_releases(matrix_file: str, output_folder: str, matrix: dict) -> None:
    """Transpile a matrix file possibly containing different os and framework
    versions (e.g. rhel6 and rhel7, py3.6 and py3.8).
    Write one dimension file for each element in the matrix
    (e.g. rhel7 and py3.8, rhel6 and py3.6)"""
    rhel_versions = matrix["rhel"]
    python_versions = matrix["py"]

    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")
    for rhel_ver, py_ver in get_matrix(rhel_versions, python_versions):
        release_dict = _pick_package_versions_for_release(
            release_matrix, rhel_ver, py_ver
        )
        filename = f"{format_release(release_base, rhel_ver, py_ver)}.yml"
        write_to_file(release_dict, os.path.join(output_folder, filename))


def combine(args):
    build_matrix_file(
        args.release_base,
        args.release_folder,
        load_yaml(args.override_mapping),
        args.py_coords,
    )


def transpile(args):
    transpile_releases(args.matrix_file, args.output_folder, args.matrix_coordinates)


def main():
    parser = argparse.ArgumentParser(
        description="Build release files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        description="Combine - build matrix file\n"
        "Transpile - generate release files",
        help="Available sub commands",
        dest="mode",
    )
    subparsers.required = True

    matrix_parser = subparsers.add_parser(
        "combine",
        description="""
Combine release files into a matrix file. Output format:

  example-package:
    rhel7:
      py36 : # package not included in release
      py38 : 5.11.13
    rhel8:
      py36 : # package not included in release
      py38 : 5.11.13+builtin""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    matrix_parser.set_defaults(func=combine)
    matrix_parser.add_argument(
        "--release-base",
        required=True,
        help="Name of the release to handle (default: None)",
    )
    matrix_parser.add_argument(
        "--release-folder",
        required=True,
        type=dir_path,
        help="Folder with existing release file (default: None)",
    )
    matrix_parser.add_argument(
        "--override-mapping",
        required=True,
        type=check_if_valid_file,
        help="File containing explicit matrix packages (default: None)",
    )

    def checkValidPythonVersion(input: str) -> list:
        output_list = []
        for item in input.split(","):
            if re.match(r"^[2,3](\.\d+)?$", item) == None:
                raise TypeError(item)
            else:
                output_list.append(item)
        return output_list

    matrix_parser.add_argument(
        "--py_coords",
        help="""Comma delimitated list of python versions to be combined,
        for example, "3.6,3.8" (without spaces).
        If None, the release files in release-folder will be used to imply
        the versions to combine.""",
        type=checkValidPythonVersion,  # lambda s: [x for x in s.split(',') if (re.match(r"^[2,3](\.\d+)?$", x) != None)],   #re.split(",", s),
        required=False,
        default=None,
    )

    transpile_parser = subparsers.add_parser(
        "transpile",
        description="Transpile a matrix file into separate release files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    transpile_parser.set_defaults(func=transpile)
    transpile_parser.add_argument(
        "--matrix-file",
        required=True,
        type=check_if_valid_file,
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
        default="{rhel: ['7'], py: ['3.8']}",
    )
    args = parser.parse_args()
    args.func(args)


def check_if_valid_file(path: str) -> str:
    if os.path.isfile(path):
        return path
    raise TypeError(path)


def dir_path(should_be_valid_path: str) -> str:
    if os.path.isdir(should_be_valid_path):
        return should_be_valid_path
    raise TypeError(should_be_valid_path)


if __name__ == "__main__":
    main()
