import argparse
import contextlib
import datetime
import os
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import jinja2
from ruamel.yaml import YAML

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
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def _locate_cmake() -> str:
    if os.path.isfile("/usr/bin/cmake3"):
        return "/usr/bin/cmake3"
    return "cmake"


def create_enable_scripts(komodo_prefix: str, komodo_release: str) -> None:
    """Render enable scripts (user facing) for bash and csh to an existing
    directory komodo_release (in current working directory).

    Args:
    ----
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


def _print_timings(
    timing_element: Tuple[str, datetime.timedelta],
    adjust: bool = False,
) -> None:
    if adjust:
        print(f" * {timing_element[0]:50} {timing_element[1]}")
    else:
        print(f" * {timing_element[0]} took {timing_element[1]}")


def _main(args):
    timings: List[Tuple[str, datetime.timedelta]] = []
    abs_prefix = Path(args.prefix).resolve()

    data = Data(extra_data_dirs=args.extra_data_dirs)

    if args.download or (not args.build and not args.install):
        start_time = datetime.datetime.now()
        git_hashes = fetch(
            args.pkgs.content,
            args.repo.content,
            outdir=args.downloads,
        )
        timings.append(("Fetching all packages", datetime.datetime.now() - start_time))
        _print_timings(timings[-1])

    if args.download and not args.build:
        sys.exit(0)

    # append root to the temporary build dir, as we want a named root/
    # directory as the distribution root, organised under the distribution name
    tmp_prefix = abs_prefix / args.release / "root"
    fakeroot = Path(args.release).resolve()
    if args.build or not args.install:
        start_time = datetime.datetime.now()
        make(
            args.pkgs.content,
            args.repo.content,
            data,
            prefix=str(tmp_prefix),
            dlprefix=args.downloads,
            builddir=args.tmp,
            fakeroot=str(fakeroot),
        )
        timings.append(
            (
                "Building non-pip part of komodo in workspace",
                datetime.datetime.now() - start_time,
            ),
        )
        _print_timings(timings[-1])

        shell(f"mv {args.release + str(tmp_prefix)} {args.release}")
        with contextlib.suppress(OSError):
            os.removedirs(f"{args.release + str(tmp_prefix.parent)}")

    if args.build and not args.install:
        sys.exit(0)

    create_enable_scripts(komodo_prefix=tmp_prefix, komodo_release=args.release)

    releasedoc = Path(args.release) / Path(args.release)
    with open(releasedoc, "w", encoding="utf-8") as filehandle:
        release = {}
        for pkg, ver in args.pkgs.content.items():
            entry = args.repo.content[pkg][ver]
            maintainer = args.repo.content[pkg][ver]["maintainer"]
            if ver == LATEST_PACKAGE_ALIAS:
                ver = latest_pypi_version(entry.get("pypi_package_name", pkg))
            elif args.repo.content[pkg][ver].get("fetch") == "git":
                ver = git_hashes[pkg]
            release[pkg] = {
                "version": ver,
                "maintainer": maintainer,
            }
        yaml = YAML()
        yaml.dump(release, filehandle)

    if args.dry_run:
        return

    print(f"Installing {args.release} to {args.prefix}")

    start_time = datetime.datetime.now()
    shell(f"mv {args.release} .{args.release}")
    shell(f"rsync -a .{args.release} {args.prefix}")
    timings.append(
        (
            "Rsyncing partial komodo to destination",
            datetime.datetime.now() - start_time,
        ),
    )
    _print_timings(timings[-1])

    if Path(f"{args.prefix}/{args.release}").exists():
        shell(
            f"mv {args.prefix}/{args.release} "
            f"{args.prefix}/{args.release}.delete-{uuid.uuid4()}",
        )

    shell(f"mv {args.prefix}/.{args.release} {args.prefix}/{args.release}")
    start_time = datetime.datetime.now()
    shell(
        f"rm -rf {args.prefix}/{args.release}.delete-*",
        allow_failure=True,
    )
    timings.append(("Deleting previous release", datetime.datetime.now() - start_time))
    _print_timings(timings[-1])

    if args.tmp:
        # Allows e.g. pip to use this folder as a destination for "pip
        # download", instead of in some cases falling back to /tmp, which is
        # undesired when building on nfs.
        os.environ["TMPDIR"] = args.tmp

    release_path = Path(args.prefix) / Path(args.release)
    release_root = release_path / "root"
    start_time = datetime.datetime.now()
    _print_timings(timings[-1])

    fixup_python_shebangs(args.prefix, args.release)

    if args.postinst:
        start_time = datetime.datetime.now()
        shell([args.postinst, release_path])
        timings.append(
            ("Running post-install scripts", datetime.datetime.now() - start_time),
        )
        _print_timings(timings[-1])

    start_time = datetime.datetime.now()
    print("running", f"find {release_root} -name '*.pyc' -delete")
    shell(f"find {release_root} -name '*.pyc' -delete")

    print("Setting permissions", [data.get("set_permissions.sh"), release_path])
    shell([data.get("set_permissions.sh"), str(release_path)])
    timings.append(
        ("Cleanup *.pyc and fix permissions", datetime.datetime.now() - start_time),
    )
    _print_timings(timings[-1])

    print("Time report:")
    for timing_element in timings:
        _print_timings(timing_element, adjust=True)


def cli_main(argv: Optional[Sequence[str]] = None):
    """Pass the command-line args to argparse, then set up the workspace."""
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.workspace and not Path(args.workspace).exists():
        Path(args.workspace).mkdir()

    os.environ["python"] = args.python

    with pushd(args.workspace):
        _main(args)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse the arguments from the command line into an `argparse.Namespace`.
    Having a separated function makes it easier to test the CLI.

    Set up the command-line interface with three groups of arguments:
      - required positional arguments
      - required named arguments
      - optional named arguments

    Args:
    ----
        args: A sequence of arguments, e.g. as collected from the command line.

    Returns:
    -------
        The `argparse.Namespace`, a mapping of arg names to values.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Welcome to Komodo. "
            "Automatically, reproducibly, and testably create software "
            "distributions."
        ),
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "pkgs",
        type=ReleaseFile(),
        help="A Komodo release file mapping package name to version, in YAML format.",
    )
    parser.add_argument(
        "repo",
        type=RepositoryFile(),
        help="A Komodo repository file, in YAML format.",
    )

    required_args = parser.add_argument_group("required named arguments")

    required_args.add_argument(
        "--prefix",
        "-p",
        type=str,
        required=True,
        help=(
            "The path of the directory in which you would like to place the "
            "built environment."
        ),
    )
    required_args.add_argument(
        "--release",
        "-r",
        type=str,
        required=True,
        help=(
            "The name of the release, will be used as the name of the directory "
            "containing the enable script and environment `root` directory."
        ),
    )
    required_args.add_argument(
        "--python",
        type=str,
        required=True,
        help="Python version to build the komodo release for",
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
        help=(
            "The directory to use for builds by cmake. None means "
            "current working directory."
        ),
    )
    optional_args.add_argument(
        "--downloads",
        "--cache",  # deprecated
        "-c",  # deprecated
        type=str,
        default="downloads",
        help=(
            "A destination directory relative to the workspace, used for downloads, "
            "used by pip download, cp, rsync and git clone. This directory "
            "must be empty if it already exists, otherwise it will be created, "
            "unless you are running with the --build option."
        ),
    )
    optional_args.add_argument(
        "--download",
        "-d",
        action="store_true",
        help=(
            "If set, packages will be downloaded but nothing will be built, unless "
            "--build is also included."
        ),
    )
    optional_args.add_argument(
        "--build",
        "-b",
        action="store_true",
        help=(
            "Flag to only build. If set and --download is not, "
            "the downloads directory must already be populated."
        ),
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
        help=(
            "Flag to choose whether stop before installing the environment. "
            "to the `prefix` location."
        ),
    )
    optional_args.add_argument(
        "--cmake",
        type=str,
        default=_locate_cmake(),
        help="The command to use for cmake builds.",
    )
    optional_args.add_argument(
        "--workspace",
        type=str,
        default=None,
        help=(
            "Directory to set as working directory during execution. "
            "None means current working directory."
        ),
    )
    optional_args.add_argument(
        "--extra-data-dirs",
        nargs="+",
        type=str,
        default=None,
        help=(
            "Directories containing extra data files for `sh` builds. "
            "Multiple directores can be given, separated with space."
        ),
    )
    optional_args.add_argument(
        "--postinst",
        "-P",
        type=str,
        help=(
            "Path to a script which will run on the release path "
            "(prefix/release) after installation."
        ),
    )

    args = parser.parse_args(argv)

    return args


if __name__ == "__main__":
    cli_main()
