#!/usr/bin/env python

import argparse
import os
import sys
from argparse import ArgumentError, ArgumentParser, ArgumentTypeError, RawTextHelpFormatter
from komodo import load_yaml, write_to_file, prettified_yaml



def build_matrix_file(release_base, release_folder, builtins):
    py27 = load_yaml("{}/{}-py27.yml".format(release_folder, release_base))

    py36 = load_yaml("{}/{}-py36.yml".format(release_folder, release_base))

    all_packages = set(py36.keys()).union(py27.keys())

    compiled = {}

    for p in all_packages:
        if p in builtins:
            compiled[p] = builtins[p]
        elif py27.get(p) == py36.get(p):
            compiled[p] = py27.get(p)
        else:
            compiled[p] = {"py27": py27.get(p), "py36": py36.get(p)}

    write_to_file(compiled, "{}.yml".format(release_base), False)

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
    release_base = os.path.basename(matrix_file).strip(".yml")
    release_folder = os.path.dirname(matrix_file)
    release_matrix = load_yaml("{}.yml".format(os.path.join(release_folder, release_base)))
    for rhel_ver in ("rhel6", "rhel7"):
        for py_ver in ("py27", "py36"):
            release_dict = _build(release_matrix, py_ver, rhel_ver)
            filename = "{rel}-{pyver}-{rhel_version}.yml".format(
                rel=release_base, pyver=py_ver, rhel_version=rhel_ver
            )
            write_to_file(release_dict, os.path.join(output_folder, filename))


def combine(args):
    build_matrix_file(args.release_base, args.release_folder, load_yaml(args.override_mapping))

def transpile(args):
    transpile_releases(args.matrix_file, args.output_folder)



def main():
    parser = ArgumentParser(description="Build release files.", formatter_class=RawTextHelpFormatter)

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
  rhel6:
    py27 : # package not included in release
    py36 : 5.11.13
  rhel7:
    py27 : # package not included in release
    py36 : 5.11.13+builtin""",
        formatter_class=RawTextHelpFormatter
    )
    matrix_parser.set_defaults(func=combine)
    matrix_parser.add_argument(
        "--release-base",
        help="Name of the release to handle",
        required=True
    )
    matrix_parser.add_argument(
        "--release-folder",
        help="Folder with existing release file",
        required=True
    )
    matrix_parser.add_argument(
        "--override-mapping",
        help="File containing explicit matrix packages",
        required=True
    )

    transpile_parser = subparsers.add_parser(
        "transpile",
        description="Transpile a matrix file into separate release files."
    )
    transpile_parser.set_defaults(func=transpile)
    transpile_parser.add_argument(
        "--matrix-file",
        help="Yaml file describing the release matrix",
        required=True
    )
    transpile_parser.add_argument(
        "--output-folder",
        help="Folder to output new release files",
        required=True
    )
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
