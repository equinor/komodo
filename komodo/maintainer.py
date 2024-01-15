#!/usr/bin/env python

from ruamel.yaml import YAML

from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def maintainers(pkgfile, repofile):
    with open(pkgfile, encoding="utf-8") as package_file_stream, open(
        repofile, encoding="utf-8"
    ) as repository_file_stream:
        yml = YAML()
        pkgs, repo = yml.load(package_file_stream), yml.load(repository_file_stream)

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
