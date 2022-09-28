#!/usr/bin/env python
from __future__ import print_function

import argparse
import logging
import os
import warnings
from collections import namedtuple

import yaml as yml
from pkg_resources import PkgResourcesDeprecationWarning, parse_version

kerr = namedtuple("KomodoError", ["pkg", "version", "maintainer", "depends", "err"])

report = namedtuple(
    "LintReport", ["release_name", "maintainers", "dependencies", "versions"]
)

MISSING_PACKAGE = "missing package"
MISSING_VERSION = "missing version"
MISSING_DEPENDENCY = "missing dependency"
MISSING_MAINTAINER = "missing maintainer"
MISSING_MAKE = "missing make information"
MALFORMED_VERSION = "malformed version"
MASTER_VERSION = "dangerous version (master branch)"
FLOAT_VERSION = "dangerous version (float interpretable)"


def _kerr(pkg=None, version=None, maintainer=None, depends=None, err=None):
    return kerr(
        pkg=pkg, version=version, maintainer=maintainer, depends=depends, err=err
    )


def _validate(pkg, ver, repo):
    if pkg not in repo:
        return _kerr(pkg=pkg, err=MISSING_PACKAGE)
    if ver not in repo[pkg]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_VERSION)
    if "maintainer" not in repo[pkg][ver]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_MAINTAINER)
    if "make" not in repo[pkg][ver]:
        return _kerr(pkg=pkg, version=ver, err=MISSING_MAKE)
    return _kerr(pkg=pkg, version=ver, maintainer=repo[pkg][ver]["maintainer"])


def lint_release_name(pkgfile):
    relname = os.path.basename(pkgfile)
    found = False
    for py_suffix in "-py27", "-py36", "-py38":
        for rh_suffix in "", "-rhel6", "-rhel7":
            if relname.endswith(py_suffix + rh_suffix + ".yml"):
                found = True
                break
    if not found:
        return [
            _kerr(
                pkg=pkgfile,
                err="Invalid release name suffix. "
                "Must be of the most -pyXX or -pyXX-rhelY",
            )
        ]

    return []


def lint_maintainers(pkgs, repo):
    return [_validate(pkg, ver, repo) for pkg, ver in pkgs.items()]


def __reg_version_err(errs, pkg, ver, maintainer, err=MALFORMED_VERSION):
    errs.append(_kerr(pkg=pkg, version=ver, maintainer=maintainer, err=err))


def lint_version_numbers(pkgs, repo):
    errs = []
    for pkg, ver in pkgs.items():
        if pkg not in repo or ver not in repo[pkg]:
            continue  # error caught previously

        pv = repo[pkg][ver]
        maintainer = pv.get("maintainer", MISSING_MAINTAINER)
        if isinstance(ver, float):
            __reg_version_err(errs, pkg, ver, maintainer, FLOAT_VERSION)
            continue

        try:
            logging.info("Using %s %s" % (pkg, ver))
            if "master" in ver:
                __reg_version_err(errs, pkg, ver, maintainer, err=MASTER_VERSION)
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", PkgResourcesDeprecationWarning)
                v = parse_version(ver)
                # A warning coincides with finding "Legacy" in repr(v)
            if "Legacy" in repr(v):  # don't know if possible to check otherwise
                __reg_version_err(errs, pkg, ver, maintainer)
        except:  # noqa
            __reg_version_err(errs, pkg, ver, maintainer)
    return errs


def lint_dependencies(pkgs, repo):
    errs = []
    for pkg, ver in pkgs.items():
        if pkg not in repo or ver not in repo[pkg]:
            continue  # error caught previously
        pv = repo[pkg][ver]
        maintainer = pv.get("maintainer", MISSING_MAINTAINER)
        if "depends" not in pv:
            continue
        missing = [d for d in pv["depends"] if d not in pkgs]
        if missing:
            errs.append(
                _kerr(
                    pkg=pkg,
                    version=ver,
                    maintainer=maintainer,
                    depends=missing,
                    err=MISSING_DEPENDENCY,
                )
            )
    return errs


def lint(pkgfile, repofile):
    if isinstance(pkgfile, dict) and isinstance(repofile, dict):
        release_name = []
        pkgs, repo = pkgfile, repofile
    else:
        release_name = lint_release_name(pkgfile)
        try:
            with open(pkgfile, "r") as p, open(repofile, "r") as r:
                pkgs, repo = yml.safe_load(p), yml.safe_load(r)
        except yml.scanner.ScannerError as err:
            raise ValueError("Malformed YAML: %s" % str(err))

    if not isinstance(pkgs, dict):
        raise ValueError("Malformed package file: %s " % str(type(pkgs)))
    if not isinstance(repo, dict):
        raise ValueError("Malformed repository file: %s" % str(type(repo)))

    mns = lint_maintainers(pkgs, repo)
    deps = lint_dependencies(pkgs, repo)
    vers = lint_version_numbers(pkgs, repo)
    return report(
        release_name=release_name, maintainers=mns, dependencies=deps, versions=vers
    )


def get_args():
    parser = argparse.ArgumentParser(description="lint komodo setup")
    parser.add_argument("pkgfile", type=str)
    parser.add_argument("repofile", type=str)
    parser.add_argument(
        "--verbose",
        help="Massive amount of outputs",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )
    args = parser.parse_args()
    return args


def lint_main():
    args = get_args()
    logging.basicConfig(format="%(message)s", level=args.loglevel)

    try:
        report = lint(args.pkgfile, args.repofile)
        mns, deps, vers = report.maintainers, report.dependencies, report.versions
    except ValueError as err:
        exit(str(err))
    print("%d packages" % len(mns))
    if not any([err.err for err in mns + deps + vers]):
        print("No errors found")
        exit(0)

    for err in mns + deps + vers:
        if err.err:
            ver = err.version if err.version else ""
            dep = ": %s" % ", ".join(err.depends) if err.depends else ""
            print("%s for %s %s%s" % (err.err, err.pkg, ver, dep))

    if not any([err.err for err in mns + deps]):
        exit(0)  # currently we allow erronous version numbers

    exit("Error in komodo configuration.")


if __name__ == "__main__":
    lint_main()
