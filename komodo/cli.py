from __future__ import print_function

import argparse
import os
import sys

import yaml as yml

import komodo
import komodo.local as local
import komodo.switch as switch
from komodo.data import Data


def _main(args):
    args.prefix = os.path.abspath(args.prefix)

    data = Data(extra_data_dirs=args.extra_data_dirs)

    if args.download or (not args.build and not args.install):
        komodo.fetch(
            args.pkgs, args.repo, outdir=args.cache, pip=args.pip, git=args.git
        )

    if args.download and not args.build:
        sys.exit(0)

    # append root to the temporary build dir, as we want a named root/
    # directory as the distribution root, organised under the distribution name
    # (release)
    tmp_prefix = os.path.join(os.path.join(args.prefix), args.release, "root")
    fakeroot = os.path.abspath(args.release)
    if args.build or not args.install:
        komodo.make(
            args.pkgs,
            args.repo,
            data,
            prefix=tmp_prefix,
            dlprefix=args.cache,
            builddir=args.tmp,
            jobs=args.jobs,
            cmk=args.cmake,
            pip=args.pip,
            virtualenv=args.virtualenv,
            fakeroot=fakeroot,
        )
        komodo.shell("mv {} {}".format(args.release + tmp_prefix, args.release))
        komodo.shell(
            "rmdir -p --ignore-fail-on-non-empty {}".format(
                os.path.dirname(args.release + tmp_prefix)
            )
        )

    if args.build and not args.install:
        sys.exit(0)

    # create the enable script
    for tmpl, target in [("enable.in", "enable"), ("enable.csh.in", "enable.csh")]:
        # if not os.path.exists(tmpl):
        #     logging.warn('Could not find template %s, skipping.' % str(tmpl))
        #     continue
        # TODO should args.release be release_path?
        with open("{}/{}".format(args.release, target), "w") as f:
            f.write(
                komodo.shell(
                    [
                        "m4 {}".format(data.get("enable.m4")),
                        "-D komodo_prefix={}".format(tmp_prefix),
                        "-D komodo_pyver={}".format(args.pyver),
                        "-D komodo_release={}".format(args.release),
                        data.get(tmpl),
                    ]
                ).decode("utf-8")
            )

    with open(args.locations_config) as defs, open(
        os.path.join(args.release, "local"), "w"
    ) as local_activator, open(
        os.path.join(args.release, "local.csh"), "w"
    ) as local_csh_activator:
        defs = yml.safe_load(defs)
        local.write_local_activators(data, defs, local_activator, local_csh_activator)

    releasedoc = os.path.join(args.release, args.release)
    with open(args.pkgs) as p, open(args.repo) as r, open(releasedoc, "w") as y:
        pkgs, repo = yml.safe_load(p), yml.safe_load(r)

        release = {}
        for pkg, ver in pkgs.items():
            release[pkg] = {"version": ver, "maintainer": repo[pkg][ver]["maintainer"]}
        yml.dump(release, y, default_flow_style=False)

    if args.dry_run:
        return

    print("Installing {} to {}".format(args.release, args.prefix))
    install_root = os.path.join(args.prefix, args.release, "root")

    komodo.shell("{1} {0} .{0} {0}".format(args.release, args.renamer))
    komodo.shell("rsync -a .{} {}".format(args.release, args.prefix), sudo=args.sudo)

    if os.path.exists("{1}/{0}".format(args.release, args.prefix)):
        komodo.shell(
            "{2} {0} {0}.delete {1}/{0}".format(
                args.release, args.prefix, args.renamer
            ),
            sudo=args.sudo,
        )

    komodo.shell(
        "{2} .{0} {0} {1}/.{0}".format(args.release, args.prefix, args.renamer),
        sudo=args.sudo,
    )
    komodo.shell(
        "rm -rf {1}/{0}.delete".format(args.release, args.prefix), sudo=args.sudo
    )

    if args.tmp:
        # Allows e.g. pip to use this folder as tmpfolder, instead of in some
        # cases falling back to /tmp, which is undesired when building on nfs.
        os.environ["TMPDIR"] = args.tmp

    print('Fixup #! in pip-provided packages if bin exist')
    release_path = os.path.join(args.prefix, args.release)
    release_root = os.path.join(release_path, "root")
    for pkg, ver in pkgs.items():
        if repo[pkg][ver]["make"] != "pip":
            continue

        shell_input = [
            args.pip,
            "install {}=={}".format(pkg, komodo.strip_version(ver)),
            "--prefix",
            release_root,
            "--no-index",
            "--no-deps",
            "--ignore-installed",
            "--cache-dir {}".format(args.cache),
            "--find-links {}".format(args.cache),
        ]
        shell_input.append(repo[pkg][ver].get("makeopts"))

        print(komodo.shell(shell_input, sudo=args.sudo))

    komodo.fixup_python_shebangs(args.prefix, args.release)

    switch.create_activator_switch(data, args.prefix, args.release)

    # run any post-install scripts on the release
    if args.postinst:
        komodo.shell([args.postinst, release_path])

    print("running", "find {} -name '*.pyc' -delete".format(release_root))
    komodo.shell("find {} -name '*.pyc' -delete".format(release_root))

    print("Setting permissions", [data.get("set_permissions.sh"), release_path])
    komodo.shell([data.get("set_permissions.sh"), release_path])


def cli_main():
    parser = argparse.ArgumentParser(description="build distribution")
    parser.add_argument("pkgs", type=str)
    parser.add_argument("repo", type=str)
    parser.add_argument("--prefix", "-p", type=str, required=True)
    parser.add_argument("--release", "-r", type=str, required=True)

    parser.add_argument("--tmp", "-t", type=str)
    parser.add_argument("--cache", "-c", type=str)
    parser.add_argument("--jobs", "-j", type=int, default=1)

    parser.add_argument("--download", "-d", action="store_true")
    parser.add_argument("--build", "-b", action="store_true")
    parser.add_argument("--install", "-i", action="store_true")
    parser.add_argument("--dry-run", "-n", action="store_true")

    parser.add_argument("--cmake", type=str, default="cmake")
    parser.add_argument("--pip", type=str, default="pip")
    parser.add_argument("--git", type=str, default="git")
    parser.add_argument(
        "--virtualenv",
        type=str,
        default="virtualenv",
        help="What virtualenv command to use",
    )
    parser.add_argument("--pyver", type=str, default="2.7")

    parser.add_argument("--sudo", action="store_true")
    parser.add_argument("--workspace", type=str, default=None)
    parser.add_argument(
        "--extra-data-dirs",
        nargs="+",
        type=str,
        default=None,
        help="Directories containing extra data files. Multiple directores can be given, separated with space.",
    )
    parser.add_argument("--postinst", "-P", type=str)
    parser.add_argument(
        "--locations-config",
        type=str,
        required=True,
        help="Path to locations.yml, a map of location to a server.",
    )

    parser.add_argument("--renamer", "-R", default="rename", type=str)

    args = parser.parse_args()

    args.pkgs = os.path.abspath(args.pkgs)
    args.repo = os.path.abspath(args.repo)

    if args.workspace and not os.path.exists(args.workspace):
        os.mkdir(args.workspace)

    with komodo.pushd(args.workspace):
        _main(args)


if __name__ == "__main__":
    cli_main()
