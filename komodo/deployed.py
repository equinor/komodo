import argparse
import re
import os
import sys


def _is_release(path):
    return os.path.isdir(os.path.realpath(path))


def _fetch_deployed_releases(install_root):
    return [
        name
        for name in os.listdir(install_root)
        if _is_release(os.path.join(install_root, name))
    ]


def _fetch_releases(release_folder):
    return [os.path.splitext(path)[0] for path in os.listdir(release_folder)]


def _fetch_non_deployed_releases(install_root, release_folder):
    deployed = _fetch_deployed_releases(install_root)
    releases = _fetch_releases(release_folder)
    return list(set(releases) - set(deployed))


def fetch_non_deployed(install_root, releases_folder, limit=None, pattern=None, remove_pattern=False):
    non_deployed = _fetch_non_deployed_releases(install_root, releases_folder)
    if pattern is not None:
        regex = re.compile(pattern)
        non_deployed = [
            release for release in non_deployed if regex.search(release) is not None
        ]
        if remove_pattern:
            non_deployed = [regex.sub("", release) for release in non_deployed]
    return non_deployed[:limit]


def deployed_main():
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the name of undeployed komodo releases given an "
            "installation root and a release folder."
        )
    )
    parser.add_argument(
        "install_root",
        type=lambda arg: os.path.realpath(arg)
        if os.path.isdir(arg)
        else parser.error("{} is not a directory".format(arg)),
        help="The root folder of the installed releases",
    )
    parser.add_argument(
        "releases_folder",
        type=lambda arg: os.path.realpath(arg)
        if os.path.isdir(arg)
        else parser.error("{} is not a directory".format(arg)),
        help="The folder containing the release folders",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="The maximum number of undeployed releases to list.",
    )
    parser.add_argument(
        "--pattern", default=".*", help="Pattern to match releases against",
    )
    parser.add_argument(
        "--remove-pattern",
        help="Remove pattern from the output strings",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    non_deployed = fetch_non_deployed(
        args.install_root,
        args.releases_folder,
        limit=args.limit,
        pattern=args.pattern,
        remove_pattern=args.remove_pattern,
    )

    if non_deployed:
        print("\n".join(non_deployed))

