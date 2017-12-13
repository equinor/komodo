#!/usr/bin/env python
from __future__ import print_function

import yaml as yml

from collections import namedtuple

kerr = namedtuple('KomodoError', ['pkg', 'version', 'maintainer', 'err'])

MISSING_PACKAGE = 'missing package'
MISSING_VERSION = 'missing version'
MISSING_MAINTAINER = 'missing maintainer'


def _kerr(pkg=None, version=None, maintainer=None, err=None):
    return kerr(pkg=pkg, version=version, maintainer=maintainer, err=err)


def _validate(pkg, ver, repo):
    if pkg not in repo:
        return _kerr(pkg=pkg, err=MISSING_PACKAGE)
    if ver not in repo[pkg]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_VERSION)
    if 'maintainer' not in repo[pkg][ver]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_MAINTAINER)
    return _kerr(pkg=pkg, version=ver, maintainer=repo[pkg][ver]['maintainer'])


def lint(pkgfile, repofile):
    with open(pkgfile) as p, open(repofile) as r:
        pkgs, repo = yml.load(p), yml.load(r)

    return [_validate(pkg, ver, repo) for pkg, ver in pkgs.items()]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='lint komodo setup')
    parser.add_argument('pkgfile', type=str)
    parser.add_argument('repofile', type=str)
    args = parser.parse_args()
    errs = lint(args.pkgfile, args.repofile)
    print('%d packages' % len(errs))
    has_error = any([err.err for err in errs])
    if not has_error:
        print('No errors found')
        exit(0)

    for err in errs:
        if err.err:
            ver = err.version if err.version else ''
            print('%s for %s %s' % (err.err, err.pkg, ver))
    exit('Error in komodo configuration.')
