import argparse
import json
import os
from typing import Optional, Sequence

from komodo.matrix import get_matrix_base
from komodo.yaml_file_types import ReleaseDir


def _is_release(path: str) -> bool:
    # some releases, like 1970.12.01-py27, will, in a matrix world, not have
    # root, which means it's just container for activation switchers.
    has_root = os.path.exists(os.path.join(path, "root"))
    return os.path.isdir(os.path.realpath(path)) and has_root


def _fetch_deployed_releases(install_root: str) -> Sequence[str]:
    return [
        get_matrix_base(name)
        for name in os.listdir(install_root)
        if _is_release(os.path.join(install_root, name))
    ]


def _fetch_releases(release_folder: str) -> Sequence[str]:
    return [os.path.splitext(path)[0] for path in os.listdir(release_folder)]


def _fetch_non_deployed_releases(
    install_root: str, release_folder: str
) -> Sequence[str]:
    deployed = _fetch_deployed_releases(install_root)
    releases = _fetch_releases(release_folder)
    return list(set(releases) - set(deployed))


def fetch_non_deployed(
    install_root: str,
    releases_folder: str,
    limit: Optional[int] = None,
) -> Sequence[str]:
    non_deployed = _fetch_non_deployed_releases(install_root, releases_folder)
    return non_deployed[:limit]


def output_formatter(release_list: Sequence[str], do_json: bool = False) -> str:
    if do_json:
        return json.dumps(release_list, separators=(",", ":"))
    return "\n".join(release_list)


def deployed_main() -> None:
    parser = argparse.ArgumentParser(
        description="""Outputs the name of undeployed matrices given an installation
            root and a release folder. A partially deployed matrix is
            considered deployed.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "install_root",
        type=lambda arg: (
            os.path.realpath(arg)
            if os.path.isdir(arg)
            else parser.error(f"{arg} is not a directory")
        ),
        help="The root folder of the deployed matrices",
    )
    parser.add_argument(
        "releases_folder",
        type=ReleaseDir(),
        help="The folder containing the matrix files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="The maximum number of undeployed matrices to list.",
    )
    parser.add_argument("--json", action="store_true", help="Get output in JSON format")

    args = parser.parse_args()
    non_deployed = fetch_non_deployed(
        args.install_root,
        args.releases_folder,
        limit=args.limit,
    )

    print(output_formatter(non_deployed, do_json=args.json))
