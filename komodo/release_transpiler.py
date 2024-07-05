#!/usr/bin/env python

import argparse
import os
from typing import Dict, Sequence, Union

import yaml

from komodo.matrix import format_release, get_matrix
from komodo.prettier import load_yaml, write_to_file


def get_py_coords(release_base: str, release_folder: str) -> Sequence[str]:
    """Get python versions of release files inside a given release_folder."""
    filenames_with_prefix = sorted(
        [
            filename
            for filename in os.listdir(release_folder)
            if filename.startswith(release_base)
        ],
    )
    len_release_base = len(release_base + "-")
    irrelevant_suffix_length = len(".yml")
    return [
        filename[len_release_base:-irrelevant_suffix_length]
        for filename in filenames_with_prefix
    ]


def _pick_package_versions_for_release(
    packages: dict,
    rhel_ver: str,
    py_ver: str,
) -> dict:
    """Consolidate the packages for a given combination of rhel and python version
    into a dictionary.
    """
    release_dict = {}
    for pkg_name, versions in packages.items():
        version = None
        try:
            _check_version_exists_for_coordinates(versions, rhel_ver, py_ver)
        except KeyError as err:
            error_msg = f"{err!s}. Failed for {pkg_name}."
            raise KeyError(error_msg) from None
        if isinstance(versions, dict):
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
    pkg_versions: Union[dict, str],
    rhel_coordinate: str,
    py_coordinate: str,
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

    """
    if isinstance(pkg_versions, str):
        return None
    first_level_versions = list(pkg_versions)
    if "rhel" in first_level_versions[0]:
        # Both rhel and python versions can have different versions
        if rhel_coordinate not in first_level_versions:
            msg = f"Rhel version {rhel_coordinate} not found."
            raise KeyError(msg)
        second_level_versions = list(pkg_versions[rhel_coordinate])
        if py_coordinate not in second_level_versions:
            msg = f"Python version {py_coordinate} not found for rhel version {rhel_coordinate}."
            raise KeyError(
                msg,
            )
    elif "py" in first_level_versions[0]:
        if py_coordinate not in first_level_versions:
            # Only python has different versions
            msg = f"Python version {py_coordinate} not found."
            raise KeyError(msg)
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
    rhel_versions = matrix["rhel"]
    python_versions = matrix["py"]

    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")
    for rhel_ver, py_ver in get_matrix(rhel_versions, python_versions):
        release_dict = _pick_package_versions_for_release(
            release_matrix,
            rhel_ver,
            py_ver,
        )
        filename = f"{format_release(release_base, rhel_ver, py_ver)}.yml"
        write_to_file(release_dict, os.path.join(output_folder, filename))


def transpile_releases_for_pip(
    matrix_file: str,
    output_folder: str,
    repository_file: str,
    matrix: dict,
) -> None:
    rhel_versions = matrix["rhel"]
    python_versions = matrix["py"]
    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")
    repository = load_yaml(repository_file)
    for rhel_ver, py_ver in get_matrix(rhel_versions, python_versions):
        release_dict = _pick_package_versions_for_release(
            release_matrix,
            rhel_ver,
            py_ver,
        )
        pip_packages = [
            f"{pkg}=={version}"
            for pkg, version in release_dict.items()
            if repository[pkg][version].get("make") == "pip"
        ]
        filename = f"{format_release(release_base, rhel_ver, py_ver)}.req"
        with open(
            os.path.join(output_folder, filename),
            mode="w",
            encoding="utf-8",
        ) as filehandler:
            filehandler.write("\n".join(pip_packages))


def transpile(args):
    transpile_releases(args.matrix_file, args.output_folder, args.matrix_coordinates)


def transpile_for_pip(args: Dict):
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
        default="{rhel: ['7'], py: ['3.8']}",
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
        default="{rhel: ['7'], py: ['3.8']}",
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
