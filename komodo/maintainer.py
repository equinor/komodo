#!/usr/bin/env python

from typing import AbstractSet, Sequence, Tuple

from ruamel.yaml import YAML

from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def maintainers(pkgfile: str, repofile: str) -> AbstractSet[Tuple[str, str, str]]:
    with open(pkgfile) as p, open(repofile) as r:
        yml = YAML()
        pkgs, repo = yml.load(p), yml.load(r)

    maints = set()
    for pkg, ver in pkgs.items():
        maints.add((pkg, ver, repo[pkg][ver]["maintainer"]))
    return maints


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Print maintainers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pkgfile",
        type=ReleaseFile(),
        help="A Komodo release file mapping package name to version, in YAML format.",
    )
    parser.add_argument(
        "repofile",
        type=RepositoryFile(),
        help="A Komodo repository file, in YAML format.",
    )
    args = parser.parse_args()
    maints = maintainers(args.pkgfile, args.repofile)
    for pkg, ver, maintainer in maints:
        print(f"{pkg} {ver} {maintainer}")
