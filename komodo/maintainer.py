#!/usr/bin/env python

import yaml as yml


def maintainers(pkgfile, repofile):
    with open(pkgfile) as p, open(repofile) as r:
        pkgs, repo = yml.safe_load(p), yml.safe_load(r)

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
        type=str,
        help="A Komodo release file mapping package name to version, "
        "in YAML format.",
    )
    parser.add_argument(
        "repofile",
        type=str,
        help="A Komodo repository file, in YAML format.",
    )
    args = parser.parse_args()
    maints = maintainers(args.pkgfile, args.repofile)
    for pkg, ver, maintainer in maints:
        print(f"{pkg} {ver} {maintainer}")
