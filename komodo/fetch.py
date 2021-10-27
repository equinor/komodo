#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys

from komodo.package_version import LATEST_PACKAGE_ALIAS, strip_version, latest_pypi_version
from komodo.shell import pushd, shell
from komodo.yaml_file_type import YamlFile


def eprint(*args, **kwargs):
    return print(*args, file = sys.stderr, **kwargs)


def grab(path, filename = None, version = None, protocol = None,
                                                pip = 'pip'):
    # guess protocol if it's obvious from the url (usually is)
    if protocol is None:
        protocol = path.split(':')[0]

    if protocol in ('http', 'https', 'ftp'):
        shell('wget --quiet {} -O {}'.format(path, filename))
    elif protocol in ('git'):
        shell(
            "git clone "
            "-b {version} "
            "-q --recursive "
            "-- {path} {filename}"
            "".format(
                version=strip_version(version),
                path=path,
                filename=filename,
            )
        )

    elif protocol in ('nfs', 'fs-ln'):
        shell('cp --recursive --symbolic-link {} {}'.format(path, filename))

    elif protocol in ('fs-cp'):
        shell('cp --recursive {} {}'.format(path, filename))

    elif protocol in ('rsync'):
        shell('rsync -a {}/ {}'.format(path, filename))
    else:
        raise NotImplementedError('Unknown protocol {}'.format(protocol))


def fetch(pkgs, repo, outdir=".", pip="pip"):
    missingpkg = [pkg for pkg in pkgs if pkg not in repo]
    missingver = [pkg for pkg, ver in pkgs.items()
                                   if pkg in repo and ver not in repo[pkg]]

    if missingpkg:
        eprint('Packages requested, but not found in the repository:')
        eprint('missingpkg: {}'.format(','.join(missingpkg)))

    for pkg in missingver:
        eprint('missingver: missing version for {}: {} requested, found: {}'.format(
                pkg, pkgs[pkg], ','.join(repo[pkg].keys()))
              )

    if missingpkg or missingver:
        return

    if outdir and not os.path.exists(outdir):
        os.mkdir(outdir)

    pypi_packages = []

    with pushd(outdir):
        for pkg, ver in pkgs.items():

            current = repo[pkg][ver]
            if "pypi_package_name" in current and current["make"] != "pip":
                raise ValueError(
                    "pypi_package_name is only valid when building with pip"
                )

            url = current.get("source")
            protocol = current.get("fetch")
            pkg_alias = current.get("pypi_package_name", pkg)

            if url == "pypi" and ver == LATEST_PACKAGE_ALIAS:
                ver = latest_pypi_version(pkg_alias)

            name = "{} ({}): {}".format(pkg_alias, ver, url)
            pkgname = "{}-{}".format(pkg_alias, ver)

            if url is None and protocol is None:
                package_folder = os.path.abspath(pkgname)
                print('Nothing to fetch for {}, but created folder {}'.format(pkgname, package_folder))
                os.mkdir(pkgname)
                continue

            dst = pkgname

            spliturl = url.split('?')[0].split('.')
            ext = spliturl[-1]

            if len(spliturl) > 1 and spliturl[-2] == 'tar':
                ext = 'tar.{}'.format(spliturl[-1])

            if ext in ['rpm', 'tar', 'gz', 'tgz', 'tar.gz', 'tar.bz2', 'tar.xz']:
                dst = '{}.{}'.format(dst, ext)

            if url == "pypi":
                print("Defering download of {}".format(name))
                pypi_packages.append(f"{pkg_alias}=={ver.split('+')[0]}")
                continue

            print('Downloading {}'.format(name))
            grab(url, filename = dst, version = ver, protocol = protocol,
                                                    pip = pip)

            if ext in ['tgz', 'tar.gz', 'tar.bz2', 'tar.xz']:
                print('Extracting {} ...'.format(dst))
                topdir = shell(' tar -xvf {}'.format(dst)).decode("utf-8").split()[0]
                normalised_dir = topdir.split('/')[0]

                if not os.path.exists(pkgname):
                    print('Creating symlink {} -> {}'.format(normalised_dir, pkgname))
                    os.symlink(normalised_dir, pkgname)

        print('Downloading {} pypi packages'.format(len(pypi_packages)))
        shell([pip, 'download', '--no-deps', '--dest .', " ".join(pypi_packages)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fetch packages")
    parser.add_argument("pkgfile", type=YamlFile())
    parser.add_argument("repofile", type=YamlFile())
    parser.add_argument("--output", "-o", type=str)
    parser.add_argument("--pip", type=str, default="pip")
    args = parser.parse_args()
    fetch(args.pkgfile, args.repofile, outdir = args.output,
                                       pip = args.pip)
