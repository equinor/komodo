import argparse
import os
import shutil
import sys
import yaml as yml

import build
import fetch
from shell import shell, pushd
from build import pypaths

def main(args):
    args.prefix = os.path.abspath(args.prefix)

    if args.download or (not args.build and not args.install):
        fetch.fetch(args.pkgs, args.repo, outdir = args.cache,
                                          pip = args.pip,
                                          git = args.git)

    if args.download and not args.build:
        sys.exit(0)

    # append root to the temporary build dir, as we want a named root/
    # directory as the distribution root, organised under the distribution name
    # (release)
    tmp_prefix = os.path.join(os.path.join(args.prefix), args.release, 'root')
    fakeroot = os.path.abspath(args.release)
    if args.build or not args.install:
        build.make(args.pkgs, args.repo, prefix   = tmp_prefix,
                                         dlprefix = args.cache,
                                         builddir = args.tmp,
                                         jobs     = args.jobs,
                                         cmk      = args.cmake,
                                         fakeroot = fakeroot)
        shell('mv {} {}'.format(args.release + tmp_prefix, args.release))
        shell('rmdir -p --ignore-fail-on-non-empty {}'.format(
            os.path.dirname(args.release + tmp_prefix)))

    if args.build and not args.install:
        sys.exit(0)

    # create the enable script
    release_path = os.path.join(args.prefix, args.release)
    for tmpl,target in [('enable.in','enable'), ('enable.csh.in', 'enable.csh')]:
        with open('{}/{}'.format(args.release, target), 'w') as f:
            f.write(shell(['m4 enable.m4',
                           '-D komodo_prefix={}'.format(tmp_prefix),
                           '-D komodo_pyver={}'.format('2.7'),
                           tmpl]))

    releasedoc = os.path.join(args.release, args.release)
    with open(args.pkgs) as p, open(args.repo) as r, open(releasedoc, 'w') as y:
        pkgs, repo = yml.load(p), yml.load(r)

        release = {}
        for pkg, ver in pkgs.items():
            release[pkg] = { 'version': ver,
                             'maintainer': repo[pkg][ver]['maintainer']
                           }
        yml.dump(release, y, default_flow_style = False)

    print('Installing {} to {}'.format(args.release, args.prefix))
    install_root = os.path.join(args.prefix, args.release, 'root')

    shell('rename {0} .{0} {0}'.format(args.release))
    shell('rsync -a .{} {}'.format(args.release, args.prefix), sudo = args.sudo)

    if os.path.exists('{1}/{0}'.format(args.release, args.prefix)):
        shell('rename {0} {0}.delete {1}/{0}'.format(args.release, args.prefix),
               sudo = args.sudo)

    shell('rename .{0} {0} {1}/.{0}'.format(args.release, args.prefix),
           sudo = args.sudo)
    shell('rm -rf {1}/{0}.delete'.format(args.release, args.prefix),
           sudo = args.sudo)

    # pip hard-codes the interpreter path to whatever interpreter that was used
    # to install it. we want this to be whatever's provided by the komodo
    # release in question, so inject the just-sync'd install and re-install
    # everything from pip
    os.environ['LD_LIBRARY_PATH'] = ':'.join([
                                        os.path.join(install_root, 'lib'),
                                        os.path.join(install_root, 'lib64'),
                                        os.environ.get('LD_LIBRARY_PATH', '')])

    os.environ['PYTHONPATH'] = pypaths(install_root, pkgs.get('python'))
    os.environ['PATH'] = ':'.join([os.path.join(install_root, 'bin'),
                                   os.environ.get('PATH', '')])

    print('Fixup #! in pip-provided packages')
    for pkg, ver in pkgs.items():
        if repo[pkg][ver]['make'] != 'pip': continue

        print(shell(['{}/bin/pip'.format(install_root),
               'install {}=={}'.format(pkg, ver),
               '--prefix', os.path.join(args.prefix, args.release, 'root'),
               '--force-reinstall',
               '--no-index',
               '--find-links {}'.format(args.cache),
               repo[pkg][ver].get('makeopts')
              ], sudo = args.sudo))

    # run any post-install scripts on the release
    if args.postinst:
        shell([args.postinst, os.path.join(args.prefix, args.release)])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'build distribution')
    parser.add_argument('pkgs', type = str)
    parser.add_argument('repo', type = str)
    parser.add_argument('--prefix', '-p',  type = str, required = True)
    parser.add_argument('--release', '-r', type = str, required = True)

    parser.add_argument('--tmp', '-t',   type = str)
    parser.add_argument('--cache', '-c', type = str)
    parser.add_argument('--jobs', '-j',  type = int, default = 1)

    parser.add_argument('--download', '-d', action = 'store_true')
    parser.add_argument('--build', '-b',    action = 'store_true')
    parser.add_argument('--install', '-i',  action = 'store_true')

    parser.add_argument('--cmake', type = str, default = 'cmake')
    parser.add_argument('--pip',   type = str, default = 'pip')
    parser.add_argument('--git',   type = str, default = 'git')

    parser.add_argument('--sudo',       action = 'store_true')
    parser.add_argument('--workspace',  type = str, default = None)
    parser.add_argument('--postinst', '-P', type = str)

    args = parser.parse_args()

    args.pkgs = os.path.abspath(args.pkgs)
    args.repo = os.path.abspath(args.repo)

    if args.workspace and not os.path.exists(args.workspace):
        os.mkdir(args.workspace)
        shutil.copy('enable.m4', args.workspace)
        shutil.copy('enable.in', args.workspace)

    with pushd(args.workspace):
        main(args)
