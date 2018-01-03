#!/usr/bin/env python
from __future__ import print_function

import yaml as yml
import logging

from collections import namedtuple

kerr = namedtuple('KomodoError',
                  ['pkg', 'version', 'maintainer', 'depends', 'err'])

MISSING_PACKAGE = 'missing package'
MISSING_VERSION = 'missing version'
MISSING_DEPENDENCY = 'missing dependency'
MISSING_MAINTAINER = 'missing maintainer'


def _kerr(pkg=None, version=None, maintainer=None, depends=None, err=None):
    return kerr(
        pkg=pkg,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err)


def _validate(pkg, ver, repo):
    if pkg not in repo:
        return _kerr(pkg=pkg, err=MISSING_PACKAGE)
    if ver not in repo[pkg]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_VERSION)
    if 'maintainer' not in repo[pkg][ver]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_MAINTAINER)
    return _kerr(pkg=pkg, version=ver, maintainer=repo[pkg][ver]['maintainer'])


def lint_maintainers(pkgs, repo):
    return [_validate(pkg, ver, repo) for pkg, ver in pkgs.items()]


def lint_dependencies(pkgs, repo):
    errs = []
    for pkg, ver in pkgs.items():
        if isinstance(ver, float):
            logging.warn('dangerous version for %s (float interpretable)' % pkg)
        pv = repo[pkg][ver]
        maintainer = pv['maintainer']
        if 'depends' not in pv:
            continue
        missing = [d for d in pv['depends'] if d not in pkgs]
        if missing:
            errs.append(
                _kerr(
                    pkg=pkg,
                    version=ver,
                    maintainer=maintainer,
                    depends=missing,
                    err=MISSING_DEPENDENCY))
    return errs


def lint(pkgfile, repofile):
    with open(pkgfile) as p, open(repofile) as r:
        pkgs, repo = yml.load(p), yml.load(r)

    mns = lint_maintainers(pkgs, repo)
    if any([err.err for err in mns]):
        return mns, []

    deps = lint_dependencies(pkgs, repo)
    return mns, deps


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='lint komodo setup')
    parser.add_argument('pkgfile', type=str)
    parser.add_argument('repofile', type=str)
    args = parser.parse_args()
    mns, deps = lint(args.pkgfile, args.repofile)
    print('%d packages' % len(mns))
    if not any([err.err for err in mns + deps]):
        print('No errors found')
        exit(0)

    for err in mns + deps:
        if err.err:
            ver = err.version if err.version else ''
            dep = ': %s' % ', '.join(err.depends) if err.depends else ''
            print('%s for %s %s%s' % (err.err, err.pkg, ver, dep))
    exit('Error in komodo configuration.')
