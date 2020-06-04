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
from komodo import elf

from .shell import shell, pushd

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

def rpm(pkg, ver, path, prefix, *args, **kwargs):
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

def cmake(pkg, ver, path, prefix, builddir,
                                  makeopts,
                                  jobs,
                                  cmake = 'cmake',
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
             '-DDEST_PREFIX={}'.format(fakeroot)
             ]

    mkpath(bdir)
    with pushd(bdir):
        print('Installing {} ({}) from source with cmake'.format(pkg, ver))
        shell([cmake, path] + flags + [makeopts])
        print(shell('make -j{}'.format(jobs)))
        print(shell('make DESTDIR={} install'.format(fakeroot)))

def sh(pkg, ver, pkgpath, prefix, makefile, *args, **kwargs):
    if os.path.isfile(makefile):
        makefile = os.path.abspath(makefile)

    with pushd(pkgpath):
        makefile = os.path.abspath(makefile)
        cmd = ['bash {} --prefix {}'.format(makefile, prefix),
               '--fakeroot {}'.format(kwargs['fakeroot']),
               '--python {}/bin/python'.format(prefix)]
        if 'jobs' in kwargs:
            cmd.append('--jobs {}'.format(kwargs['jobs']))
        if 'cmake' in kwargs:
            cmd.append('--cmake {}'.format(kwargs['cmake']))
        cmd.append(kwargs.get('makeopts'))

        print('Installing {} ({}) from sh'.format(pkg, ver))
        shell(cmd)

def rsync(pkg, ver, pkgpath, prefix, *args, **kwargs):
    print('Installing {} ({}) with rsync'.format(pkg, ver))
    # assume a root-like layout in the pkgpath dir, and just copy it
    shell(['rsync -am', kwargs.get('makeopts'), '{}/'.format(pkgpath), kwargs['fakeroot'] + prefix])


def pip_install(pkg, ver, pkgpath, prefix, dlprefix, pip='pip', *args, **kwargs):
    cmd = [pip,
           'install {}=={}'.format(pkg, komodo.strip_version(ver)),
           '--root {}'.format(kwargs['fakeroot']),
           '--prefix {}'.format(prefix),
           '--no-index',
           '--no-deps',
           '--find-links {}'.format(dlprefix),
           kwargs.get('makeopts', '')]

    print('Installing {} ({}) from pip'.format(pkg, ver))
    shell(cmd)

def pypaths(prefix, version):
    if version is None: return ''
    pyver = 'python' + '.'.join(version.split('.')[:-1])
    return ':'.join([ '{0}/lib/{1}'.format(prefix, pyver),
                      '{0}/lib/{1}/site-packages'.format(prefix, pyver),
                      '{0}/lib64/{1}/site-packages'.format(prefix, pyver) ])

def make(pkgfile, repofile, prefix = None,
                            dlprefix = None,
                            builddir = None,
                            jobs = 1,
                            cmk = 'cmake',
                            pip = 'pip',
                            fakeroot = '.'):
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
    os.mkdir(os.path.join(fakeprefix, "lib"))
    os.symlink(os.path.join(fakeprefix, "lib"), os.path.join(fakeprefix, "lib64"))
    prefix = os.path.abspath(prefix)

    # assuming there always is a python *and* that python will be installed
    # before pip is required. This dependency *must* be explicit in the
    # repository
    os.environ['DESTDIR'] = fakeroot
    os.environ['PYTHONPATH'] = pypaths(fakeprefix, pkgs.get('python'))
    os.environ['BOOST_ROOT'] = fakeprefix
    os.environ['PATH'] = ':'.join([os.path.join(fakeprefix, 'bin'),
                                   os.environ['PATH']])
    os.environ['LD_LIBRARY_PATH'] = ':'.join(filter(None,
                                           [os.path.join(fakeprefix, 'lib'),
                                            os.environ.get('LD_LIBRARY_PATH')]))
    rpath = os.path.join(prefix, "lib")
    os.environ['LDFLAGS'] = "-Wl,-rpath," + rpath
    extra_makeopts = os.environ.get('extra_makeopts')

    pkgpaths = ['{}-{}'.format(pkg, pkgs[pkg]) for pkg in pkgorder]
    if dlprefix:
        pkgpaths = [os.path.join(dlprefix, path) for path in pkgpaths]

    def resolve(x):
        return x.replace('$(prefix)', prefix)

    build = { 'rpm': rpm, 'cmake': cmake, 'sh': sh, 'pip': pip_install, 'rsync': rsync }

    for pkg, path in zip(pkgorder, pkgpaths):
        ver = pkgs[pkg]
        current = repo[pkg][ver]
        make = current['make']
        pkgpath = os.path.abspath(path)

        if extra_makeopts:
            oldopts = current.get('makeopts', '')
            current['makeopts'] = ' '.join((oldopts, extra_makeopts))

        current['makeopts'] = resolve(current.get('makeopts', ''))
        build[make](pkg, ver, pkgpath, prefix = prefix,
                                       builddir = builddir,
                                       makeopts = current.get('makeopts'),
                                       makefile = current.get('makefile'),
                                       dlprefix = dlprefix if dlprefix else '.',
                                       jobs     = jobs,
                                       cmake    = cmk,
                                       pip      = pip,
                                       fakeroot = fakeroot)

        if current.get("fixup_rpaths", False):
            elf.patch_all(root, rpath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'build packages')
    parser.add_argument('pkgfile',  type=str)
    parser.add_argument('repofile', type=str)
    parser.add_argument('--prefix', '-p', type=str)
    parser.add_argument('--dlprefix', '-d', type=str)
    parser.add_argument('--build', '-b', type=str)
    parser.add_argument('--jobs', '-j', type=int, default = 1)
    parser.add_argument('--cmake', type=str, default = 'cmake')
    parser.add_argument('--fakeroot', action = 'store_true')

    fakeroot = args.prefix if args.fakeroot else '.'
    args = parser.parse_args()
    make(args.pkgfile, args.repofile, prefix = args.prefix,
                                      dlprefix = args.dlprefix,
                                      builddir = args.build,
                                      fakeroot = fakeroot)
