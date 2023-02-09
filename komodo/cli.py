import argparse
import os
import sys
import warnings
from pathlib import Path
from typing import List

import jinja2
import yaml as yml

from komodo import local, switch
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


def create_enable_scripts(komodo_prefix: str, komodo_release: str) -> None:
    """Render enable scripts (user facing) for bash and csh to an existing
    directory komodo_release (in current working directory).

    Args:
        komodo_prefix: The filesystem path to where the release is to be
            deployed.
        komodo_release: The name of the release.
    """
    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader(package_name="komodo", package_path="data"),
        keep_trailing_newline=True,
    )
    for tmpl, target in [
        ("enable.jinja2", "enable"),
        ("enable.csh.jinja2", "enable.csh"),
    ]:
        (Path(komodo_release) / target).write_text(
            jinja_env.get_template(tmpl).render(
                komodo_prefix=komodo_prefix,
                komodo_release=komodo_release,
            ),
            encoding="utf-8",
        )


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

    create_enable_scripts(komodo_prefix=tmp_prefix, komodo_release=args.release)

    if args.locations_config is not None:
        with open(args.locations_config, mode="r", encoding="utf-8") as defs, open(
            Path(args.release) / "local", mode="w", encoding="utf-8"
        ) as local_activator, open(
            Path(args.release) / "local.csh", mode="w", encoding="utf-8"
        ) as local_csh_activator:
            defs = yml.safe_load(defs)
            local.write_local_activators(
                data, defs, local_activator, local_csh_activator
            )

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

    shell(f"mv {args.release} .{args.release}")
    shell(f"rsync -a .{args.release} {args.prefix}", sudo=args.sudo)

    if Path(f"{args.prefix}/{args.release}").exists():
        shell(
            f"mv {args.prefix}/{args.release} {args.prefix}/{args.release}.delete",
            sudo=args.sudo,
        )

    shell(
        f"mv {args.prefix}/.{args.release} {args.prefix}/{args.release}",
        sudo=args.sudo,
    )
    shell(f"rm -rf {args.prefix}/{args.release}.delete", sudo=args.sudo)

    if args.tmp:
        # Allows e.g. pip to use this folder as tmpfolder, instead of in some
        # cases falling back to /tmp, which is undesired when building on nfs.
        os.environ["TMPDIR"] = args.tmp

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
    """
    Pass the command-line args to argparse, then set up the workspace.
    """
    args = parse_args(sys.argv[1:])

    if args.workspace and not Path(args.workspace).exists():
        Path(args.workspace).mkdir()

    with pushd(args.workspace):
        _main(args)


def parse_args(args: List[str]) -> argparse.Namespace:
    """
    Parse the arguments from the command line into an `argparse.Namespace`.
    Having a separated function makes it easier to test the CLI.

    Set up the command-line interface with three groups of arguments:
      - required positional arguments
      - required named arguments
      - optional named arguments

    Args:
        args: A sequence of arguments, e.g. as collected from the command line.

    Returns:
        The `argparse.Namespace`, a mapping of arg names to values.
    """
    parser = argparse.ArgumentParser(
        description="Welcome to Komodo. "
        "Automatically, reproducibly, and testably create software "
        "distributions.",
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "pkgs",
        type=YamlFile(),
        help="A Komodo release file mapping package name to version, "
        "in YAML format.",
    )
    parser.add_argument(
        "repo",
        type=YamlFile(),
        help="A Komodo repository file, in YAML format.",
    )

    required_args = parser.add_argument_group("required named arguments")

    required_args.add_argument(
        "--prefix",
        "-p",
        type=str,
        required=True,
        help="The path of the directory in which you would like to place the "
        "built environment.",
    )
    required_args.add_argument(
        "--release",
        "-r",
        type=str,
        required=True,
        help="The name of the release, will be used as the name of the directory "
        "containing the enable script and environment `root` directory.",
    )

    optional_args = parser.add_argument_group("optional arguments")

    optional_args.add_argument(
        "--help",
        "-h",
        action="help",
        help="Show this help message and exit.",
    )
    optional_args.add_argument(
        "--tmp",
        "-t",
        type=str,
        help="The directory to use for builds by cmake. None means "
        "current working directory.",
    )
    optional_args.add_argument(
        "--cache",
        "-c",
        type=str,
        default="pip-cache",
        help="The temporary directory used for downloads, e.g. by pip.",
    )
    optional_args.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="The number of parallel jobs to use for builds by cmake.",
    )
    optional_args.add_argument(
        "--download",
        "-d",
        action="store_true",
        help="Flag to choose whether to download the packages.",
    )
    optional_args.add_argument(
        "--build",
        "-b",
        action="store_true",
        help="Flag to choose whether to build the packages.",
    )
    optional_args.add_argument(
        "--install",
        "-i",
        action="store_true",
        help="Flag to choose whether to create enable scripts and manifest file.",
    )
    optional_args.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Flag to choose whether stop before installing the environment. "
        "to the `prefix` location.",
    )
    optional_args.add_argument(
        "--cmake",
        type=str,
        default="cmake",
        help="The command to use for cmake builds.",
    )
    optional_args.add_argument(
        "--pip",
        type=str,
        default="pip",
        help="The command to use for pip builds.",
    )
    optional_args.add_argument(
        "--virtualenv",
        type=str,
        default="virtualenv",
        help="The command to use for virtual environment construction.",
    )
    optional_args.add_argument(
        "--pyver",
        type=str,
        help="[DEPRECATED] This argument is not used.",  # Message to stderr below.
    )
    optional_args.add_argument(
        "--sudo",
        action="store_true",
        help="Flag to choose whether to use `sudo` for shell commands when "
        "installing the environment.",
    )
    optional_args.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="Directory to set as working directory during execution. "
        "None means current working directory.",
    )
    optional_args.add_argument(
        "--extra-data-dirs",
        nargs="+",
        type=str,
        default=None,
        help="Directories containing extra data files for `sh` builds. "
        "Multiple directores can be given, separated with space.",
    )
    optional_args.add_argument(
        "--postinst",
        "-P",
        type=str,
        help="Path to a script which will run on the release path "
        "(prefix/release) after installation.",
    )
    required_args.add_argument(
        "--locations-config",
        type=str,
        help="Path to a YAML file defining a dictionary available to "
        "shell script templates.",
    )

    args = parser.parse_args(args)

    if args.pyver is not None:
        message = (
            "\n\n⚠️  The --pyver option is deprecated and will be removed in a "
            "future version of komodo. It is not used by komodo.\n"
        )
        warnings.warn(message, FutureWarning, stacklevel=2)

    return args


if __name__ == "__main__":
    cli_main()
