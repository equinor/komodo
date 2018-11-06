#!/usr/bin/env python

import contextlib
import json
import urllib2

from distutils import version as dv

def _strict_stable(versions):
    rcfixer = lambda x : x.replace('rc', 'b999').replace('.dev', 'a0')
    fixed = map(rcfixer, versions)
    for elt in fixed:
        try:
            sv = dv.StrictVersion(elt)
            if not sv.prerelease:
                yield sv
        except:
            pass

def _pip_versions(pkg):
    path = 'https://pypi.python.org/pypi/{}/json'.format(pkg)
    with contextlib.closing(urllib2.urlopen(urllib2.Request(path))) as x:
        js = json.load(x)
    versions = js['releases'].keys()
    try:
        fixed_versions = list(reversed(sorted(_strict_stable(versions))))
        if fixed_versions:
            return [fixed_versions[0]]
    except:
        pass
    try:
        versions.sort(key=dv.StrictVersion)
    except ValueError as e:
        versions.sort(key=dv.LooseVersion)
    return versions

def _pip_latest(pkg):
    version_ = str(_pip_versions(pkg)[-1])
    if version_.count('.') == 1:
        return version_ + '.0'
    return version_

def pip_latest_versions(pkgs):
    if isinstance(pkgs, str):
        pkgs = [pkgs]
    print('\n'.join(['{}: {}'.format(pkg, _pip_latest(pkg)) for pkg in pkgs]))

if __name__ == '__main__':
    from sys import argv
    if len(argv) < 2:
        exit('Usage: versions pkg [pkg2 pkg3 ... pkgn]')
    pip_latest_versions(argv[1:])
