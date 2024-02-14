import argparse
import contextlib
import datetime
import os
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import jinja2
from ruamel.yaml import YAML

import komodo.switch
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


class KomodoNamespace(argparse.Namespace):
    """
    Komodo argument parser namespace
    """

    pkgs: ReleaseFile
    repo: RepositoryFile
    prefix: str
    release: str
    tmp: str
    downloads: str
    jobs: int
    download: bool
    build: bool
    install: bool
    dry_run: bool
    overwrite: bool
    cmake: str
    pip: str
    pyver: Optional[str]
    workspace: str
    extra_data_dirs: List[str]
    postinst: str


def profile_time(msg: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fun: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.datetime.now()
            res = fun(*args, **kwargs)
            timings.append(
                (msg, datetime.datetime.now() - start_time),
            )
            _print_timing(timings[-1])
            return res

        return wrapper

    return decorator


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


def _print_timing(
    timing_element: Tuple[str, datetime.timedelta],
    adjust: bool = False,
) -> None:
    if adjust:
        print(f" * {timing_element[0]:50} {timing_element[1]}")
    else:
        print(f" * {timing_element[0]} took {timing_element[1]}")


def check_for_possible_build_overwrite(
    release_path: Path, overwrite_enabled: bool = False
) -> None:
    """Checks for possible overwrite of prior build.

    Args:
        release_path: The path where the new release will be built.
        overwrite_enabled: Flag to enable overwriting of prior release build. Defaults to False.

    Raises:
        RuntimeError: if prior release build is detected,
        --overwrite flag is not set, and build is not 'bleeding'.
    """
    if release_path.exists() and not (
        overwrite_enabled or "bleeding" in str(release_path)
    ):
        raise RuntimeError(
            "Only bleeding builds can be overwritten unless --overwrite is supplied"
        )


def is_download_only(args: KomodoNamespace) -> bool:
    return args.download and not args.build


@profile_time("Fetching all packages")
def download_packages(
    release_file_content: Mapping[str, str],
    repository_file_content: Mapping[str, Mapping[str, Union[str, Sequence[str]]]],
    download_destination: str,
    pip_executable: str = "pip",
) -> Dict[str, str]:
    """Downloads all PyPI packages to destination. Tries to download other
        packages to destination too.
    Git packages are collected, and a dict of all git hashes is returned.

    Args:
    ----
    release_file_content: A mapping of all packages and versions to be
        included in the release.
    repository_file_content: A mapping of all available packages and
        versions that can be included in a release.
    download_destination: A string of the path where packages should
        be downloaded to
    pip_executable: A string of the pip executable to use. Defaults to 'pip'

    Returns:
    --
    Dict of git hashes found
    """
    git_hashes = fetch(
        release_file_content,
        repository_file_content,
        outdir=download_destination,
        pip=pip_executable,
    )

    return git_hashes


@profile_time("Building non-pip part of komodo in workspace")
def _make(*args, **kwargs) -> None:
    make(*args, **kwargs)


def build_packages_and_move_to_release_path(
    args: KomodoNamespace, data: Data, tmp_prefix: Path
):
    fakeroot = Path(args.release).resolve()
    _make(
        args.pkgs.content,
        args.repo.content,
        data,
        prefix=str(tmp_prefix),
        dlprefix=args.downloads,
        builddir=args.tmp,
        jobs=args.jobs,
        cmk=args.cmake,
        pip=args.pip,
        fakeroot=str(fakeroot),
    )

    shell(f"mv {args.release + str(tmp_prefix)} {args.release}")
    with contextlib.suppress(OSError):
        os.removedirs(f"{args.release + str(tmp_prefix.parent)}")


def is_build_only(args: KomodoNamespace) -> bool:
    return args.build and not args.install


def generate_general_release_packages(release_path: Path) -> Path:
    """Append root to the temporary build dir, as we want a named root/
    directory as the distribution root, organised under the distribution name

    Args:
        release_path (Path):

    Returns:
        release_root
    """
    abs_prefix = release_path.resolve()
    return abs_prefix / "root"


def generate_release_packages(
    release_name: Path,
    release_file_content: Mapping[str, str],
    repository_file_content: Mapping[str, Mapping[str, Union[str, Sequence[str]]]],
    git_hashes: Optional[Mapping[str, str]] = None,
) -> None:
    releasedoc = Path(release_name) / Path(release_name)
    with open(releasedoc, mode="w", encoding="utf-8") as filehandle:
        release: Dict[str, Dict[str, str]] = {}
        for package, version in release_file_content.items():
            entry: Dict[str, str] = repository_file_content[package][version]
            maintainer = repository_file_content[package][version]["maintainer"]
            if version == LATEST_PACKAGE_ALIAS:
                version = latest_pypi_version(entry.get("pypi_package_name", package))
            elif entry.get("fetch") == "git":
                version = git_hashes[package]
            release[package] = {
                "version": version,
                "maintainer": maintainer,
            }
        yaml = YAML()
        yaml.dump(release, filehandle)


@profile_time("Rsyncing partial komodo to destination")
def rsync_komodo_to_destination(release_name: str, destination: str) -> None:
    shell(f"mv {release_name} .{release_name}")
    shell(f"rsync -a .{release_name} {destination}")


def move_old_release_from_release_path_if_exists(release_path: Path) -> None:
    if release_path.exists():
        shell(f"mv {str(release_path)} " f"{str(release_path)}.delete-{uuid.uuid4()}")


def move_new_release_to_release_path(args: KomodoNamespace, release_path: Path) -> None:
    shell(f"mv {args.prefix}/.{args.release} {str(release_path)}")


@profile_time("Deleting previous release")
def delete_old_previously_moved_releases(prefix_path: Path, release_name: Path) -> None:

    release_dir_glob = [
        str(p.absolute()) for p in list(prefix_path.glob(f"{release_name}.delete-*"))
    ]
    shell(
        "rm -rf -- " + " ".join(release_dir_glob),
        allow_failure=True,
    )


def apply_fallback_tmpdir_for_pip_if_set(tmp_dir: Optional[str] = None):
    """Allows e.g. pip to use this folder as a destination for "pip
    download", instead of in some cases falling back to /tmp, which is
    undesired when building on nfs.

    Args:
        tmp_dir (Optional): Directory for pip to use as fallback.
    """
    if tmp_dir:
        os.environ["TMPDIR"] = tmp_dir


@profile_time("pip install to final destination")
def install_previously_downloaded_pip_packages(
    release_file_content: Mapping[str, str],
    repository_file_content: Mapping[str, Mapping[str, Union[str, Sequence[str]]]],
    downloads_directory: str,
    pip_executable: str,
    release_root: Path,
) -> None:
    for pkg, ver in release_file_content.items():
        current = repository_file_content[pkg][ver]
        if current["make"] != "pip":
            continue

        package_name = current.get("pypi_package_name", pkg)
        if ver == LATEST_PACKAGE_ALIAS:
            ver = latest_pypi_version(package_name)
        shell_input = [
            pip_executable,
            f"install {package_name}=={strip_version(ver)}",
            "--prefix",
            str(release_root),
            "--no-index",
            "--no-deps",
            "--ignore-installed",
            # assuming fetch.py has done "pip download" to this directory:
            f"--cache-dir {downloads_directory}",
            f"--find-links {downloads_directory}",
        ]
        shell_input.append(current.get("makeopts"))

        print(shell(shell_input))


def run_post_installation_scripts_if_set(
    postinst: Optional[str], release_path: Path
) -> None:
    if postinst:
        timing_func = profile_time("Running post-install scripts")
        timing_func(shell([postinst, release_path]))


@profile_time("find and delete python bytecode files")
def find_and_delete_python_bytecode_files(release_root: Path) -> None:
    print("running", f"find {release_root} -name '*.pyc' -delete")
    shell(f"find {release_root} -name '*.pyc' -delete")


@profile_time("set permissions")
def set_permissions(set_permissions_script: Path, release_path: Path) -> None:
    print("Setting permissions", [set_permissions_script, release_path])
    shell([str(set_permissions_script), str(release_path)])


def cleanup_python_bytecode_files_and_fix_permissions(
    release_root: Path, set_permissions_script_path, release_path: Path
):
    find_and_delete_python_bytecode_files(release_root)
    set_permissions(set_permissions_script_path, release_path)


timings: List[Tuple[str, datetime.timedelta]] = []


def _main(args: KomodoNamespace) -> None:
    """Create a Komodo release.

    Args:
    ----
        args: KomodoNamespace instance with configuration
    """
    data = Data(extra_data_dirs=args.extra_data_dirs)

    if args.download or (not args.build and not args.install):
        git_hashes = download_packages(
            args.pkgs.content,
            args.repo.content,
            download_destination=args.downloads,
            pip_executable=args.pip,
        )
        if is_download_only(args):
            sys.exit(0)

    prefix_path = Path(args.prefix)
    release_path = prefix_path / args.release
    check_for_possible_build_overwrite(
        release_path=release_path, overwrite_enabled=args.overwrite
    )

    release_root = generate_general_release_packages(release_path)

    if args.build or not args.install:
        build_packages_and_move_to_release_path(args, data, release_root)
        if is_build_only(args):
            sys.exit(0)

    create_enable_scripts(komodo_prefix=release_root, komodo_release=args.release)

    generate_release_packages(
        args.release, args.pkgs.content, args.repo.content, git_hashes
    )

    if args.dry_run:
        return

    print(f"Installing {args.release} to {args.prefix}")

    rsync_komodo_to_destination(args.release, destination=prefix_path)

    move_old_release_from_release_path_if_exists(release_path)
    move_new_release_to_release_path(args, release_path)
    delete_old_previously_moved_releases(prefix_path, args.release)

    apply_fallback_tmpdir_for_pip_if_set(args.tmp)

    install_previously_downloaded_pip_packages(
        args.pkgs.content,
        args.repo.content,
        downloads_directory=args.downloads,
        pip_executable=args.pip,
        release_root=release_root,
    )
    fixup_python_shebangs(args.prefix, args.release)

    komodo.switch.create_activator_switch(data, args.prefix, args.release)

    run_post_installation_scripts_if_set(args.postinst, release_path)
    cleanup_python_bytecode_files_and_fix_permissions(
        release_root,
        set_permissions_script_path=data.get("set_permissions.sh"),
        release_path=release_path,
    )

    print("Time report:")
    for timing_element in timings:
        _print_timing(timing_element, adjust=True)


def cli_main():
    """Pass the command-line args to argparse, then set up the workspace."""
    args = parse_args(sys.argv[1:])

    if args.workspace and not Path(args.workspace).exists():
        Path(args.workspace).mkdir()

    with pushd(args.workspace):
        _main(args)


def parse_args(args: List[str]) -> KomodoNamespace:
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
        "--overwrite",
        action="store_true",
        help=(
            "If set, any existing release will be overwritten. "
            "If `bleeding` is part of the release name, this is impliclity true."
        ),
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
        "--pyver",
        type=str,
        help="[DEPRECATED] This argument is not used.",  # Message to stderr below.
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

    args: KomodoNamespace = parser.parse_args(args, namespace=KomodoNamespace())

    if args.pyver is not None:
        message = (
            "\n\n⚠️  The --pyver option is deprecated and will be removed in a "
            "future version of komodo. It is not used by komodo.\n"
        )
        warnings.warn(message, FutureWarning, stacklevel=2)

    return args


if __name__ == "__main__":
    cli_main()
