from __future__ import print_function

import argparse
import os
import sys
from pathlib import Path

import yaml as yml

import komodo.local as local
import komodo.switch as switch
from komodo.build import make
from komodo.data import Data
from komodo.fetch import fetch
from komodo.package_version import (
    LATEST_PACKAGE_ALIAS,
    latest_pypi_version,
    strip_version,
)
from komodo.shebang import fixup_python_shebangs
from komodo.shell import pushd, shell
from komodo.yaml_file_type import YamlFile


def _main(args):
    abs_prefix = Path(args.prefix).resolve()

    data = Data(extra_data_dirs=args.extra_data_dirs)

    if args.download or (not args.build and not args.install):
        git_hashes = fetch(args.pkgs, args.repo, outdir=args.cache, pip=args.pip)

    if args.download and not args.build:
        sys.exit(0)

    # append root to the temporary build dir, as we want a named root/
    # directory as the distribution root, organised under the distribution name
    # (release)
    tmp_prefix = abs_prefix / args.release / "root"
    fakeroot = Path(args.release).resolve()
    if args.build or not args.install:
        make(
            args.pkgs,
            args.repo,
            data,
            prefix=str(tmp_prefix),
            dlprefix=args.cache,
            builddir=args.tmp,
            jobs=args.jobs,
            cmk=args.cmake,
            pip=args.pip,
            virtualenv=args.virtualenv,
            fakeroot=str(fakeroot),
        )
        shell(f"mv {args.release + str(tmp_prefix)} {args.release}")
        shell(
            "rmdir -p --ignore-fail-on-non-empty "
            f"{args.release + str(tmp_prefix.parent)}"
        )

    if args.build and not args.install:
        sys.exit(0)

    # create the enable script
    for tmpl, target in [("enable.in", "enable"), ("enable.csh.in", "enable.csh")]:
        # TODO should args.release be release_path?
        with open(f"{args.release}/{target}", mode="w", encoding="utf-8") as f_handle:
            f_handle.write(
                shell(
                    [
                        f"m4 {data.get('enable.m4')}",
                        f"-D komodo_prefix={tmp_prefix}",
                        f"-D komodo_pyver={args.pyver}",
                        f"-D komodo_release={args.release}",
                        data.get(tmpl),
                    ]
                ).decode("utf-8")
            )

    with open(args.locations_config, mode="r", encoding="utf-8") as defs, open(
        Path(args.release) / "local", mode="w", encoding="utf-8"
    ) as local_activator, open(
        Path(args.release) / "local.csh", mode="w", encoding="utf-8"
    ) as local_csh_activator:
        defs = yml.safe_load(defs)
        local.write_local_activators(data, defs, local_activator, local_csh_activator)

    releasedoc = Path(args.release) / Path(args.release)
    with open(releasedoc, "w", encoding="utf-8") as filehandle:
        release = {}
        for pkg, ver in args.pkgs.items():
            entry = args.repo[pkg][ver]
            maintainer = args.repo[pkg][ver]["maintainer"]
            if ver == LATEST_PACKAGE_ALIAS:
                ver = latest_pypi_version(entry.get("pypi_package_name", pkg))
            elif args.repo[pkg][ver].get("fetch") == "git":
                ver = git_hashes[pkg]
            release[pkg] = {
                "version": ver,
                "maintainer": maintainer,
            }
        yml.dump(release, filehandle, default_flow_style=False)

    if args.dry_run:
        return

    print(f"Installing {args.release} to {args.prefix}")

    shell(f"{args.renamer} {args.release} .{args.release} {args.release}")
    shell(f"rsync -a .{args.release} {args.prefix}", sudo=args.sudo)

    if Path(f"{args.prefix}/{args.release}").exists():
        shell(
            f"{args.renamer} {args.release} "
            f"{args.release}.delete {args.prefix}/{args.release}",
            sudo=args.sudo,
        )

    shell(
        f"{args.renamer} .{args.release} {args.release} {args.prefix}/.{args.release}",
        sudo=args.sudo,
    )
    shell(f"rm -rf {args.prefix}/{args.release}.delete", sudo=args.sudo)

    if args.tmp:
        # Allows e.g. pip to use this folder as tmpfolder, instead of in some
        # cases falling back to /tmp, which is undesired when building on nfs.
        os.environ["TMPDIR"] = args.tmp

    print("Fixup #! in pip-provided packages if bin exist")
    release_path = Path(args.prefix) / Path(args.release)
    release_root = release_path / "root"
    for pkg, ver in args.pkgs.items():
        current = args.repo[pkg][ver]
        if current["make"] != "pip":
            continue

        package_name = current.get("pypi_package_name", pkg)
        if ver == LATEST_PACKAGE_ALIAS:
            ver = latest_pypi_version(package_name)
        shell_input = [
            args.pip,
            f"install {package_name}=={strip_version(ver)}",
            "--prefix",
            str(release_root),
            "--no-index",
            "--no-deps",
            "--ignore-installed",
            f"--cache-dir {args.cache}",
            f"--find-links {args.cache}",
        ]
        shell_input.append(current.get("makeopts"))

        print(shell(shell_input, sudo=args.sudo))

    fixup_python_shebangs(args.prefix, args.release)

    switch.create_activator_switch(data, args.prefix, args.release)

    # run any post-install scripts on the release
    if args.postinst:
        shell([args.postinst, release_path])

    print("running", f"find {release_root} -name '*.pyc' -delete")
    shell(f"find {release_root} -name '*.pyc' -delete")

    print("Setting permissions", [data.get("set_permissions.sh"), release_path])
    shell([data.get("set_permissions.sh"), str(release_path)])


def cli_main():
    parser = argparse.ArgumentParser(description="build distribution")
    parser.add_argument("pkgs", type=YamlFile())
    parser.add_argument("repo", type=YamlFile())
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
    parser.add_argument(
        "--virtualenv",
        type=str,
        default="virtualenv",
        help="What virtualenv command to use",
    )
    parser.add_argument("--pyver", type=str, default="3.8")

    parser.add_argument("--sudo", action="store_true")
    parser.add_argument("--workspace", type=str, default=None)
    parser.add_argument(
        "--extra-data-dirs",
        nargs="+",
        type=str,
        default=None,
        help="Directories containing extra data files. "
        "Multiple directores can be given, separated with space.",
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

    if args.workspace and not Path(args.workspace).exists():
        Path(args.workspace).mkdir()

    with pushd(args.workspace):
        _main(args)


if __name__ == "__main__":
    cli_main()
