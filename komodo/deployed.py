import argparse
import re
import os
import sys
from builtins import map
from komodo.matrix import get_matrix, format_release, get_matrix_base


def _is_release(path):
    # some releases, like 1970.12.01-py27, will, in a matrix world, not have
    # root, which means it's just container for activation switchers.
    has_root = os.path.exists(os.path.join(path, "root"))
    return os.path.isdir(os.path.realpath(path)) and has_root


def _fetch_deployed_releases(install_root):
    return [
        get_matrix_base(name)
        for name in os.listdir(install_root)
        if _is_release(os.path.join(install_root, name))
    ]


def _fetch_releases(release_folder):
    return [os.path.splitext(path)[0] for path in os.listdir(release_folder)]


def _fetch_non_deployed_releases(install_root, release_folder):
    deployed = _fetch_deployed_releases(install_root)
    releases = _fetch_releases(release_folder)
    return list(set(releases) - set(deployed))


def fetch_non_deployed(install_root, releases_folder, limit=None):
    non_deployed = _fetch_non_deployed_releases(install_root, releases_folder)
    return non_deployed[:limit]


def deployed_main():
    parser = argparse.ArgumentParser(
        description=(
            """Outputs the name of undeployed matrices given an installation
            root and a release folder. A partially deployed matrix is
            considered deployed."""
        )
    )
    parser.add_argument(
        "install_root",
        type=lambda arg: os.path.realpath(arg)
        if os.path.isdir(arg)
        else parser.error("{} is not a directory".format(arg)),
        help="The root folder of the deployed matrices",
    )
    parser.add_argument(
        "releases_folder",
        type=lambda arg: os.path.realpath(arg)
        if os.path.isdir(arg)
        else parser.error("{} is not a directory".format(arg)),
        help="The folder containing the matrix files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="The maximum number of undeployed matrices to list.",
    )

    args = parser.parse_args()
    non_deployed = fetch_non_deployed(
        args.install_root,
        args.releases_folder,
        limit=args.limit,
    )

    if non_deployed:
        print("\n".join(non_deployed))
