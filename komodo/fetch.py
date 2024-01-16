#!/usr/bin/env python


import argparse
import os
import sys

import jinja2

from komodo.package_version import (
    LATEST_PACKAGE_ALIAS,
    get_git_revision_hash,
    latest_pypi_version,
    strip_version,
)
from komodo.shell import pushd, shell
from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def eprint(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)


def grab(path, filename=None, version=None, protocol=None, pip="pip"):
    # guess protocol if it's obvious from the url (usually is)
    if protocol is None:
        protocol = path.split(":")[0]

    if protocol in ("http", "https", "ftp"):
        shell(f"wget --quiet {path} -O {filename}")
    elif protocol in ("git"):
        if os.path.exists(filename):
            return
        shell(
            "git clone "
            f"-b {strip_version(version)} "
            "--quiet "
            "--recurse-submodules "
            f"-- {path} {filename}",
        )

    elif protocol in ("nfs", "fs-ln"):
        if sys.platform == "darwin":
            shell(f"cp -Rs {path} {filename}")
        else:
            shell(f"cp --recursive --symbolic-link {path} {filename}")

    elif protocol in ("fs-cp"):
        if sys.platform == "darwin":
            shell(f"cp -R {path} {filename}")
        else:
            shell(f"cp --recursive {path} {filename}")

    elif protocol in ("rsync"):
        shell(f"rsync -a {path}/ {filename}")
    else:
        msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(msg)


def fetch(pkgs, repo, outdir, pip="pip") -> dict:
    python = os.environ["python"]
    missingpkg = [pkg for pkg in pkgs if pkg not in repo]
    missingver = [
        pkg for pkg, ver in pkgs.items() if pkg in repo and ver not in repo[pkg]
    ]

    if missingpkg:
        eprint("Packages requested, but not found in the repository:")
        eprint("missingpkg: " + ",".join(missingpkg))

    for pkg in missingver:
        eprint(
            f"missingver: missing version for {pkg}: {pkgs[pkg]} requested, "
            f"found: {','.join(repo[pkg].keys())}",
        )

    if missingpkg or missingver:
        return {}

    if not outdir:
        msg = "The value of `outdir`, the download destination location cannot be None or the empty string."
        raise ValueError(
            msg,
        )
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    pypi_packages = []

    git_hashes = {}
    with pushd(outdir):
        for pkg, ver in pkgs.items():
            current = repo[pkg][ver]
            if "pypi_package_name" in current and current["make"] != "pip":
                msg = "pypi_package_name is only valid when building with pip"
                raise ValueError(
                    msg,
                )

            if "source" in current:
                templater = jinja2.Environment(loader=jinja2.BaseLoader).from_string(
                    current.get("source"),
                )
                url = templater.render(os.environ)
            else:
                url = None

            protocol = current.get("fetch")
            pkg_alias = current.get("pypi_package_name", pkg)

            if url == "pypi" and ver == LATEST_PACKAGE_ALIAS:
                ver = latest_pypi_version(pkg_alias)

            name = f"{pkg_alias} ({ver}): {url}"
            pkgname = f"{pkg_alias}-{ver}"

            if url is None and protocol is None:
                package_folder = os.path.abspath(pkgname)
                print(
                    f"Nothing to fetch for {pkgname}, "
                    f"but created folder {package_folder}",
                )
                os.makedirs(pkgname, exist_ok=True)
                continue

            dst = pkgname

            spliturl = url.split("?")[0].split(".")
            ext = spliturl[-1]

            if len(spliturl) > 1 and spliturl[-2] == "tar":
                ext = f"tar.{spliturl[-1]}"

            if ext in ["rpm", "tar", "gz", "tgz", "tar.gz", "tar.bz2", "tar.xz"]:
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
                topdir = shell(f"tar -xvf {dst}").decode("utf-8").split()[0]
                normalised_dir = topdir.split("/")[0]

                if not os.path.exists(pkgname):
                    print(f"Creating symlink {normalised_dir} -> {pkgname}")
                    os.symlink(normalised_dir, pkgname)

        print(f"Downloading {len(pypi_packages)} pypi packages")
        shell(
            [
                pip,
                "--python",
                python,
                "download",
                "--no-deps",
                "--dest .",
                " ".join(pypi_packages),
            ]
        )

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
    )
