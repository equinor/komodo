#!/usr/bin/env python


import hashlib
import itertools as itr
import os
import pathlib
import stat
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Sequence, TypedDict

import requests

from komodo.data import Data
from komodo.package_version import (
    LATEST_PACKAGE_ALIAS,
    latest_pypi_version,
    strip_version,
)
from komodo.shell import run, run_env

flatten = itr.chain.from_iterable


class _PackageInfo(TypedDict):
    pypi_package_name: str
    depends: Sequence[str]
    make: str
    makeopts: str
    makefile: str
    url: str
    destination: str
    hash: str


_Packages = Mapping[str, str]
_Repository = Mapping[str, Mapping[str, _PackageInfo]]


class _Make(Protocol):
    def __call__(
        self,
        pkg: str,
        ver: str,
        path: str,
        data: Data,
        *,
        prefix: str,
        builddir: Optional[str],
        makeopts: Optional[str],
        makefile: Optional[str],
        dlprefix: Optional[str],
        jobs: int,
        cmake: str,
        pip: str,
        virtualenv: Optional[str],
        fakeroot: str,
        pythonpath: str,
        binpath: str,
        ld_lib_path: Optional[str],
        url: Optional[str],
        destination: Optional[str],
        hash_: Optional[str],
    ) -> None:
        ...


def dfs(pkg: str, version: str, pkgs: _Packages, repo: _Repository) -> Iterable[str]:
    # package has no more dependencies - add the package itself
    if "depends" not in repo[pkg][version]:
        return [pkg]

    if not all(map(pkgs.__contains__, repo[pkg][version]["depends"])):
        print(
            "error: "
            + ",".join(repo[pkg][version]["depends"])
            + " required as dependency, is not in distribution",
            file=sys.stderr,
        )
        sys.exit(1)

    # dependencies can change based on version (i.e. version 2 depends on
    # package X, but version 3 depends on X and Y)
    dependencies = [dfs(x, pkgs[x], pkgs, repo) for x in repo[pkg][version]["depends"]]
    dependencies.append([pkg])
    return flatten(dependencies)


# When running cmake we pass the option -DDEST_PREFIX=fakeroot, this is an
# absolute hack to be able to build opm-common and sunbeam with the ~fakeroot
# implementation used by komodo.
#
# See sunbeam/CMakeLists.txt for a more detailed description of the issue.
# When/if the opm project updates the generated opm-common-config.cmake to work
# with "make DESTDIR=" the DEST_PREFIX cmake flag can be removed.


def cmake(
    pkg: str,
    ver: str,
    path: str,
    data: Data,
    *,
    prefix: str,
    builddir: Optional[str],
    makeopts: Optional[str],
    makefile: Optional[str],
    dlprefix: Optional[str],
    jobs: int,
    cmake: str,
    pip: str,
    virtualenv: Optional[str],
    fakeroot: str,
    pythonpath: str,
    binpath: str,
    ld_lib_path: Optional[str],
    url: Optional[str],
    destination: Optional[str],
    hash_: Optional[str],
) -> None:
    bdir = f"{pkg}-{ver}-build"
    if builddir is not None:
        bdir = os.path.join(builddir, bdir)

    fakeprefix = fakeroot + prefix

    flags = [
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DBOOST_ROOT={fakeprefix}",
        "-DBUILD_SHARED_LIBS=ON",
        f"-DCMAKE_PREFIX_PATH={fakeprefix}",
        f"-DCMAKE_MODULE_PATH={fakeprefix}/share/cmake/Modules",
        f"-DCMAKE_INSTALL_PREFIX={prefix}",
        f"-DDEST_PREFIX={fakeroot}",
    ]

    Path(bdir).mkdir(parents=True, exist_ok=True)
    setenv: Dict[str, str] = {}
    if ld_lib_path:
        setenv["LD_LIBRARY_PATH"] = ld_lib_path
    if binpath:
        setenv["PATH"] = binpath

    print(f"Installing {pkg} ({ver}) from source with cmake")
    with run_env(setenv=setenv, cwd=bdir) as run:
        run(cmake, path, *flags, *((makeopts or "").split()))
        print(run("make", f"-j{jobs}"))
        print(run("make", f"DESTDIR={fakeroot}", "install"))


def sh(
    pkg: str,
    ver: str,
    path: str,
    data: Data,
    *,
    prefix: str,
    builddir: Optional[str],
    makeopts: Optional[str],
    makefile: Optional[str],
    dlprefix: Optional[str],
    jobs: int,
    cmake: str,
    pip: str,
    virtualenv: Optional[str],
    fakeroot: str,
    pythonpath: str,
    binpath: str,
    ld_lib_path: Optional[str],
    url: Optional[str],
    destination: Optional[str],
    hash_: Optional[str],
) -> None:
    assert makefile is not None

    cmd = [
        "bash",
        makefile,
        "--prefix",
        prefix,
        f"--fakeroot={fakeroot}",
        f"--python={prefix}/bin/python",
        f"--pythonpath={pythonpath}",
        f"--binpath={binpath}",
        f"--pip={pip}",
        f"--virtualenv={virtualenv}",
        f"--ld-library-path={ld_lib_path}",
        f"--jobs={jobs}",
        f"--cmake={cmake}",
        *(makeopts or "").split(),
    ]

    print(f"Installing {pkg} ({ver}) from sh")
    run(*cmd, cwd=prefix)


def rsync(
    pkg: str,
    ver: str,
    path: str,
    data: Data,
    *,
    prefix: str,
    builddir: Optional[str],
    makeopts: Optional[str],
    makefile: Optional[str],
    dlprefix: Optional[str],
    jobs: int,
    cmake: str,
    pip: str,
    virtualenv: Optional[str],
    fakeroot: str,
    pythonpath: str,
    binpath: str,
    ld_lib_path: Optional[str],
    url: Optional[str],
    destination: Optional[str],
    hash_: Optional[str],
) -> None:
    print(f"Installing {pkg} ({ver}) with rsync")
    # assume a root-like layout in the pkgpath dir, and just copy it
    run(
        "rsync",
        "-am",
        *(makeopts or "").split(),
        f"{path}/",
        f"{fakeroot}{prefix}",
    )


def download(
    pkg: str,
    ver: str,
    path: str,
    data: Data,
    *,
    prefix: str,
    builddir: Optional[str],
    makeopts: Optional[str],
    makefile: Optional[str],
    dlprefix: Optional[str],
    jobs: int,
    cmake: str,
    pip: str,
    virtualenv: Optional[str],
    fakeroot: str,
    pythonpath: str,
    binpath: str,
    ld_lib_path: Optional[str],
    url: Optional[str],
    destination: Optional[str],
    hash_: Optional[str],
) -> None:
    assert url is not None
    assert hash_ is not None
    assert destination is not None

    print(f"Installing {pkg} ({ver}) with download")

    if not url.startswith("https"):
        msg = f"{url} does not use https:// protocol"
        raise ValueError(msg)

    hash_type, hash_value = hash_.split(":")
    if hash_type != "sha256":
        msg = f"Hash type {hash_type} given - only sha256 implemented"
        raise NotImplementedError(
            msg,
        )

    fakeprefix = pathlib.Path(fakeroot + prefix)
    dest_path = fakeprefix / destination

    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=20))
    response = session.get(url, stream=True)

    if response.status_code != 200:
        msg = f"GET request to {url} returned status code {response.status_code}"
        raise RuntimeError(
            msg,
        )

    sha256 = hashlib.sha256()

    with open(dest_path, "wb") as file_handle:
        for chunk in response.iter_content(chunk_size=1024):
            file_handle.write(chunk)
            sha256.update(chunk)

    if sha256.hexdigest() != hash_value:
        msg = f"Hash of downloaded file ({sha256.hexdigest()}) not equal to expected hash."
        raise ValueError(
            msg,
        )

    # Add executable permission if in bin folder:
    if "bin" in dest_path.parts:
        dest_path.chmod(
            dest_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )


def pip_install(
    pkg: str,
    ver: str,
    path: str,
    data: Data,
    *,
    prefix: str,
    builddir: Optional[str],
    makeopts: Optional[str],
    makefile: Optional[str],
    dlprefix: Optional[str],
    jobs: int,
    cmake: str,
    pip: str,
    virtualenv: Optional[str],
    fakeroot: str,
    pythonpath: str,
    binpath: str,
    ld_lib_path: Optional[str],
    url: Optional[str],
    destination: Optional[str],
    hash_: Optional[str],
) -> None:
    ver = strip_version(ver)
    if ver == LATEST_PACKAGE_ALIAS:
        ver = latest_pypi_version(pkg) or "none"
    cmd = [
        pip,
        "install",
        f"{pkg}=={strip_version(ver)}",
        f"--root={fakeroot}",
        f"--prefix={prefix}",
        "--no-index",
        "--no-deps",
        "--ignore-installed",
    ]
    if dlprefix:
        cmd.extend(["--cache-dir", dlprefix, "--find-links", dlprefix])
    cmd.extend((makeopts or "").split())

    print(f"Installing {pkg} ({ver}) from pip")
    run(*cmd)


def noop(pkg: str, ver: str, *args: Any, **kwargs: Any) -> None:
    print(f"Doing nothing for noop package {pkg} ({ver})")


def pypaths(prefix: str, version: Optional[str]) -> str:
    if version is None:
        return ""
    pyver = "python" + ".".join(version.split(".")[:-1])
    return ":".join(
        [
            f"{prefix}/lib/{pyver}",
            f"{prefix}/lib/{pyver}/site-packages",
            f"{prefix}/lib64/{pyver}/site-packages",
        ],
    )


def make(
    pkgs: _Packages,
    repo: _Repository,
    data: Data,
    prefix: str,
    dlprefix: Optional[str] = None,
    builddir: Optional[str] = None,
    jobs: int = 1,
    cmk: str = "cmake",
    pip: str = "pip",
    virtualenv: Optional[str] = None,
    fakeroot: str = ".",
) -> None:
    xs = flatten(dfs(pkg, ver, pkgs, repo) for pkg, ver in pkgs.items())

    seen = set()
    pkgorder = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        pkgorder.append(x)

    fakeprefix = fakeroot + prefix
    run("mkdir", "-p", fakeprefix)
    prefix = os.path.abspath(prefix)

    # assuming there always is a python *and* that python will be installed
    # before pip is required. This dependency *must* be explicit in the
    # repository
    os.environ["DESTDIR"] = fakeroot
    os.environ["BOOST_ROOT"] = fakeprefix
    build_ld_lib_path = ":".join(
        filter(
            None,
            [
                os.path.join(fakeprefix, "lib"),
                os.path.join(fakeprefix, "lib64"),
                os.environ.get("LD_LIBRARY_PATH"),
            ],
        ),
    )
    extra_makeopts = os.environ.get("EXTRA_MAKEOPTS")
    build_pythonpath = pypaths(fakeprefix, pkgs.get("python"))
    build_path = ":".join([os.path.join(fakeprefix, "bin"), os.environ["PATH"]])

    pkgpaths = [f"{pkg}-{pkgs[pkg]}" for pkg in pkgorder]
    if dlprefix:
        pkgpaths = [os.path.join(dlprefix, path) for path in pkgpaths]

    build: Mapping[str, _Make] = {
        "cmake": cmake,
        "sh": sh,
        "pip": pip_install,
        "rsync": rsync,
        "noop": noop,
        "download": download,
    }

    for pkg, path in zip(pkgorder, pkgpaths):
        ver = pkgs[pkg]
        current = repo[pkg][ver]
        make = current["make"]
        pkgpath = os.path.abspath(path)

        download_keys = ["url", "destination", "hash"]
        if any(key in current for key in download_keys) and make != "download":
            raise ValueError(
                ", ".join(download_keys) + " only valid with 'make: download'",
            )
        if not all(key in current for key in download_keys) and make == "download":
            raise ValueError(
                ", ".join(download_keys) + " all required with 'make: download'",
            )

        if "pypi_package_name" in current and make != "pip":
            msg = "pypi_package_name is only valid when building with pip"
            raise ValueError(msg)

        package_name = current.get("pypi_package_name", pkg)

        if extra_makeopts:
            oldopts = current.get("makeopts", "")
            current["makeopts"] = f"{oldopts} {extra_makeopts}"

        build[make](
            package_name,
            ver,
            pkgpath,
            data,
            prefix=prefix,
            builddir=builddir,
            makeopts=current.get("makeopts"),
            makefile=current.get("makefile"),
            dlprefix=dlprefix,
            jobs=jobs,
            cmake=cmk,
            pip=pip,
            virtualenv=virtualenv,
            fakeroot=fakeroot,
            pythonpath=build_pythonpath,
            binpath=build_path,
            ld_lib_path=build_ld_lib_path,
            url=current.get("url"),
            destination=current.get("destination"),
            hash_=current.get("hash"),
        )
