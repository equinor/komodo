#!/usr/bin/env python


import argparse
import os
import sys
from typing import Any, Mapping, Optional

import jinja2

from komodo.package_version import (
    LATEST_PACKAGE_ALIAS,
    get_git_revision_hash,
    latest_pypi_version,
    strip_version,
)
from komodo.shell import run, run_env
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def grab(
    path: str, filename: str, version: str, protocol: str, pip: str = "pip"
) -> None:
    # guess protocol if it's obvious from the url (usually is)
    if protocol is None:
        protocol = path.split(":")[0]

    if protocol in ("http", "https", "ftp"):
        run("wget", "--quiet", path, "-O", filename)
    elif protocol in ("git"):
        run(
            "git",
            "clone",
            "-b",
            strip_version(version),
            "--quiet",
            "--recurse-submodules",
            "--",
            path,
            filename,
        )

    elif protocol in ("nfs", "fs-ln"):
        run("cp", "-Rs", path, filename)

    elif protocol in ("fs-cp"):
        run("cp", "-R", path, filename)

    elif protocol in ("rsync"):
        run("rsync", "-a", f"{path}/", filename)
    else:
        msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(msg)


def fetch(
    pkgs: Mapping[str, str], repo: Mapping[str, Any], outdir: str, pip: str = "pip"
) -> Mapping[str, str]:
    missingpkg = [pkg for pkg in pkgs if pkg not in repo]
    missingver = [
        pkg for pkg, ver in pkgs.items() if pkg in repo and ver not in repo[pkg]
    ]

    if missingpkg:
        print("Packages requested, but not found in the repository:", file=sys.stderr)
        print("missingpkg: " + ",".join(missingpkg), file=sys.stderr)

    for pkg in missingver:
        print(
            f"missingver: missing version for {pkg}: {pkgs[pkg]} requested, "
            f"found: {','.join(repo[pkg].keys())}",
            file=sys.stderr,
        )

    if missingpkg or missingver:
        return {}

    if not outdir:
        msg = "The value of `outdir`, the download destination location cannot be None or the empty string."
        raise ValueError(
            msg,
        )
    if os.path.exists(outdir) and os.listdir(outdir):
        msg = f"Downloading to non-empty directory {outdir} is not supported."
        raise RuntimeError(
            msg,
        )
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    pypi_packages = []

    git_hashes = {}
    with run_env(cwd=outdir) as run:
        for pkg, ver in pkgs.items():
            current = repo[pkg][ver]
            if "pypi_package_name" in current and current["make"] != "pip":
                msg = "pypi_package_name is only valid when building with pip"
                raise ValueError(
                    msg,
                )

            url: Optional[str] = None
            if "source" in current:
                templater = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
                    current.get("source"),
                )
                url = templater.render(os.environ)

            protocol = current.get("fetch")
            pkg_alias = current.get("pypi_package_name", pkg)

            if url == "pypi" and ver == LATEST_PACKAGE_ALIAS:
                ver = latest_pypi_version(pkg_alias) or ""

            name = f"{pkg_alias} ({ver}): {url}"
            pkgname = f"{pkg_alias}-{ver}"

            if url is None and protocol is None:
                package_folder = os.path.abspath(pkgname)
                print(
                    f"Nothing to fetch for {pkgname}, "
                    f"but created folder {package_folder}",
                )
                os.mkdir(pkgname)
                continue

            dst = pkgname

            assert url is not None
            spliturl = url.split("?")[0].split(".")
            ext = spliturl[-1]

            if len(spliturl) > 1 and spliturl[-2] == "tar":
                ext = f"tar.{spliturl[-1]}"

            if ext in ["tar", "gz", "tgz", "tar.gz", "tar.bz2", "tar.xz"]:
                dst = f"{dst}.{ext}"

            if url == "pypi":
                print(f"Deferring download of {name}")
                pypi_packages.append(f"{pkg_alias}=={ver.split('+')[0]}")
                continue

            print(f"Downloading {name}")
            grab(url, filename=dst, version=ver, protocol=protocol, pip=pip)

            if protocol == "git":
                git_hashes[pkg] = get_git_revision_hash(path=dst)

            if ext in ["tgz", "tar.gz", "tar.bz2", "tar.xz"]:
                print(f"Extracting {dst} ...")
                topdir = run("tar", "-xvf", dst).decode("utf-8").split()[0]
                normalised_dir = topdir.split("/")[0]

                if not os.path.exists(pkgname):
                    print(f"Creating symlink {normalised_dir} -> {pkgname}")
                    os.symlink(normalised_dir, pkgname)

        print(f"Downloading {len(pypi_packages)} pypi packages")
        run(pip, "download", "--no-deps", "--dest", ".", *pypi_packages)

    return git_hashes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="fetch packages",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pkgfile",
        type=ReleaseFile(),
        help="A Komodo release file mapping package name to version, in YAML format.",
    )
    parser.add_argument(
        "repofile",
        type=RepositoryFile(),
        help="A Komodo repository file, in YAML format.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help=(
            "The download destination for pip, cp, rsync and git. "
            "Must be non-existing or empty."
        ),
    )
    parser.add_argument(
        "--pip",
        type=str,
        default="pip",
        help="The command to use for downloading pip packages.",
    )
    args = parser.parse_args()
    fetch(
        args.content.pkgfile,
        args.content.repofile,
        outdir=args.content.output,
        pip=args.pip,
    )
