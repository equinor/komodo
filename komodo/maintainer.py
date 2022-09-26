#!/usr/bin/env python
from __future__ import print_function

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

    parser = argparse.ArgumentParser(description="print maintainers")
    parser.add_argument("pkgfile", type=str)
    parser.add_argument("repofile", type=str)
    args = parser.parse_args()
    maints = maintainers(args.pkgfile, args.repofile)
    for pkg, ver, maintainer in maints:
        print("%s %s %s" % (pkg, ver, maintainer))
