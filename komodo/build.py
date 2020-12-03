#!/usr/bin/env python

from __future__ import print_function

import argparse
from distutils.dir_util import mkpath
import itertools as itr
import os
import subprocess
import sys
import yaml as yml
import komodo
import sys

from .shell import shell, pushd
from komodo.data import Data


flatten = itr.chain.from_iterable

def dfs(pkg, version, pkgs, repo):

    # package has no more dependencies - add the package itself
    if 'depends' not in repo[pkg][version]: return [pkg]

    if not all(map(pkgs.__contains__, repo[pkg][version]['depends'])):
        print('error: {} required as dependency, is not in distribution'.format(
              ','.join(repo[pkg][version]['depends'])), file = sys.stderr)
        sys.exit(1)

    # dependencies can change based on version (i.e. version 2 depends on
    # package X, but version 3 depends on X and Y)
    dependencies = [dfs(x, pkgs[x], pkgs, repo)
                    for x in repo[pkg][version]['depends']]
    dependencies.append([pkg])
    return flatten(dependencies)


def rpm(pkg, ver, path, data, prefix, *args, **kwargs):
    # cpio always outputs to cwd, can't be overriden with switches
    with pushd(prefix):
        print('Installing {} ({}) from rpm'.format(pkg, ver))
        shell('rpm2cpio {}.rpm | cpio -imd --quiet'.format(path))
        shell('rsync -a usr/* .')
        shell('rm -rf usr')


# When running cmake we pass the option -DDEST_PREFIX=fakeroot, this is an
# absolute hack to be able to build opm-common and sunbeam with the ~fakeroot
# implementation used by komodo.
#
# See sunbeam/CMakeLists.txt for a more detailed description of the issue.
# When/if the opm project updates the generated opm-common-config.cmake to work
# with "make DESTDIR=" the DEST_PREFIX cmake flag can be removed.

def cmake(pkg, ver, path, data, prefix, builddir, makeopts, jobs,
          cmake='cmake',
          *args, **kwargs):
    bdir = '{}-{}-build'.format(pkg, ver)
    if builddir is not None:
        bdir = os.path.join(builddir, bdir)

    fakeroot = kwargs['fakeroot']
    fakeprefix = fakeroot + prefix

    flags = ['-DCMAKE_BUILD_TYPE=Release',
             '-DBOOST_ROOT={}'.format(fakeprefix),
             '-DBUILD_SHARED_LIBS=ON',
             '-DCMAKE_PREFIX_PATH={}'.format(fakeprefix),
             '-DCMAKE_MODULE_PATH={}/share/cmake/Modules'.format(fakeprefix),
             '-DCMAKE_INSTALL_PREFIX={}'.format(prefix),
             '-DDEST_PREFIX={}'.format(fakeroot),
             ]

    mkpath(bdir)
    with pushd(bdir):
        os.environ["LD_LIBRARY_PATH"] = kwargs.get("ld_lib_path")
        _pre_PATH = os.environ["PATH"]
        os.environ["PATH"] = kwargs.get("binpath")

        print('Installing {} ({}) from source with cmake'.format(pkg, ver))
        shell([cmake, path] + flags + [makeopts])
        print(shell('make -j{}'.format(jobs)))
        print(shell('make DESTDIR={} install'.format(fakeroot)))

        del os.environ["LD_LIBRARY_PATH"]
        os.environ["PATH"] = _pre_PATH


def sh(pkg, ver, pkgpath, data, prefix, makefile, *args, **kwargs):
    makefile = data.get(makefile)

    with pushd(pkgpath):
        cmd = ['bash {} --prefix {}'.format(makefile, prefix),
               '--fakeroot {}'.format(kwargs['fakeroot']),
               '--python {}/bin/python'.format(prefix)]
        if 'jobs' in kwargs:
            cmd.append('--jobs {}'.format(kwargs['jobs']))
        if 'cmake' in kwargs:
            cmd.append('--cmake {}'.format(kwargs['cmake']))
        cmd.append('--pythonpath {}'.format(kwargs['pythonpath']))
        cmd.append('--path {}'.format(kwargs['binpath']))
        cmd.append('--pip {}'.format(kwargs['pip']))
        cmd.append('--virtualenv {}'.format(kwargs['virtualenv']))
        cmd.append('--ld-library-path {}'.format(kwargs['ld_lib_path']))
        cmd.append(kwargs.get('makeopts'))

        print('Installing {} ({}) from sh'.format(pkg, ver))
        shell(cmd)


def rsync(pkg, ver, pkgpath, data, prefix, *args, **kwargs):
    print('Installing {} ({}) with rsync'.format(pkg, ver))
    # assume a root-like layout in the pkgpath dir, and just copy it
    shell(['rsync -am', kwargs.get('makeopts'), '{}/'.format(pkgpath), kwargs['fakeroot'] + prefix])


def pip_install(pkg, ver, pkgpath, data, prefix, dlprefix, pip='pip', *args, **kwargs):
    cmd = [pip,
           'install {}=={}'.format(pkg, komodo.strip_version(ver)),
           '--root {}'.format(kwargs['fakeroot']),
           '--prefix {}'.format(prefix),
           '--no-index',
           '--no-deps',
           '--ignore-installed',
           '--cache-dir {}'.format(dlprefix),
           '--find-links {}'.format(dlprefix),
           kwargs.get('makeopts', ''),
    ]

    print('Installing {} ({}) from pip'.format(pkg, ver))
    shell(cmd)


def noop(pkg, ver, *args, **kwargs):
    print('Doing nothing for noop package {} ({})'.format(pkg, ver))
    pass


def pypaths(prefix, version):
    if version is None: return ''
    pyver = 'python' + '.'.join(version.split('.')[:-1])
    return ':'.join([ '{0}/lib/{1}'.format(prefix, pyver),
                      '{0}/lib/{1}/site-packages'.format(prefix, pyver),
                      '{0}/lib64/{1}/site-packages'.format(prefix, pyver) ])


def make(pkgfile, repofile, data,
         prefix=None,
         dlprefix=None,
         builddir=None,
         jobs=1,
         cmk='cmake',
         pip='pip',
         virtualenv=None,
         fakeroot='.',):
    with open(pkgfile) as p, open(repofile) as r:
        pkgs, repo = yml.safe_load(p), yml.safe_load(r)

    xs = flatten(dfs(pkg, ver, pkgs, repo) for pkg, ver in pkgs.items())

    seen = set()
    pkgorder = []
    for x in xs:
        if x in seen: continue
        seen.add(x)
        pkgorder.append(x)

    fakeprefix = fakeroot + prefix
    shell(['mkdir -p', fakeprefix])
    prefix = os.path.abspath(prefix)

    # assuming there always is a python *and* that python will be installed
    # before pip is required. This dependency *must* be explicit in the
    # repository
    os.environ['DESTDIR'] = fakeroot
    os.environ['BOOST_ROOT'] = fakeprefix
    build_ld_lib_path = ':'.join(filter(None,
                                            [os.path.join(fakeprefix, 'lib'),
                                            os.path.join(fakeprefix, 'lib64'),
                                            os.environ.get('LD_LIBRARY_PATH')]))
    extra_makeopts = os.environ.get('extra_makeopts')
    build_pythonpath = pypaths(fakeprefix, pkgs.get('python'))
    build_path = ':'.join([os.path.join(fakeprefix, 'bin'), os.environ['PATH']])

    pkgpaths = ['{}-{}'.format(pkg, pkgs[pkg]) for pkg in pkgorder]
    if dlprefix:
        pkgpaths = [os.path.join(dlprefix, path) for path in pkgpaths]

    def resolve(x):
        return x.replace('$(prefix)', prefix)

    build = { 'rpm': rpm, 'cmake': cmake, 'sh': sh, 'pip': pip_install, 'rsync': rsync, 'noop': noop }

    for pkg, path in zip(pkgorder, pkgpaths):
        ver = pkgs[pkg]
        current = repo[pkg][ver]
        make = current['make']
        pkgpath = os.path.abspath(path)
        if "pypi_package_name" in current and make != "pip":
            raise ValueError("pypi_package_name is only valid when building with pip")

        package_name = current.get("pypi_package_name", pkg)

        if extra_makeopts:
            oldopts = current.get("makeopts", "")
            current["makeopts"] = " ".join((oldopts, extra_makeopts))

        current["makeopts"] = resolve(current.get("makeopts", ""))
        build[make](
            package_name,
            ver,
            pkgpath,
            data,
            prefix=prefix,
            builddir=builddir,
            makeopts=current.get("makeopts"),
            makefile=current.get("makefile"),
            dlprefix=dlprefix if dlprefix else ".",
            jobs=jobs,
            cmake=cmk,
            pip=pip,
            virtualenv=virtualenv,
            fakeroot=fakeroot,
            pythonpath=build_pythonpath,
            binpath=build_path,
            ld_lib_path=build_ld_lib_path,
        )
