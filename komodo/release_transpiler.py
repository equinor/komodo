#!/usr/bin/env python

import itertools
import os
from argparse import ArgumentParser, RawTextHelpFormatter

from komodo.matrix import format_release, get_matrix
from komodo.prettier import load_yaml, write_to_file


def build_matrix_file(release_base, release_folder, builtins):
    files = {}
    py_keys = [py_ver for _, py_ver in get_matrix()]
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


def _build(packages, py_ver, rhel_ver):
    release_dict = {}
    for p, versions in packages.items():
        if rhel_ver in versions:
            version = versions[rhel_ver][py_ver]
        elif py_ver in versions:
            version = versions[py_ver]
        else:
            version = versions

        if version:
            release_dict[p] = version
    return release_dict


def transpile_releases(matrix_file, output_folder):
    release_base = os.path.splitext(os.path.basename(matrix_file))[0]
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml(f"{os.path.join(release_folder, release_base)}.yml")
    for rhel_ver, py_ver in get_matrix():
        release_dict = _build(release_matrix, py_ver, rhel_ver)
        filename = f"{format_release(release_base, rhel_ver, py_ver)}.yml"
        write_to_file(release_dict, os.path.join(output_folder, filename))


def combine(args):
    build_matrix_file(
        args.release_base, args.release_folder, load_yaml(args.override_mapping)
    )


def transpile(args):
    transpile_releases(args.matrix_file, args.output_folder)


def main():
    parser = ArgumentParser(
        description="Build release files.", formatter_class=RawTextHelpFormatter
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
Combine release files into a matrix file.
Output format:
example-package:
  rhel7:
    py36 : # package not included in release
    py38 : 5.11.13
  rhel8:
    py36 : # package not included in release
    py38 : 5.11.13+builtin""",
        formatter_class=RawTextHelpFormatter,
    )
    matrix_parser.set_defaults(func=combine)
    matrix_parser.add_argument(
        "--release-base", help="Name of the release to handle", required=True
    )
    matrix_parser.add_argument(
        "--release-folder", help="Folder with existing release file", required=True
    )
    matrix_parser.add_argument(
        "--override-mapping",
        help="File containing explicit matrix packages",
        required=True,
    )

    transpile_parser = subparsers.add_parser(
        "transpile", description="Transpile a matrix file into separate release files."
    )
    transpile_parser.set_defaults(func=transpile)
    transpile_parser.add_argument(
        "--matrix-file", help="Yaml file describing the release matrix", required=True
    )
    transpile_parser.add_argument(
        "--output-folder", help="Folder to output new release files", required=True
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
