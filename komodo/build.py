#!/usr/bin/env python


import hashlib
import itertools as itr
import os
import pathlib
import stat
import sys
from pathlib import Path
from typing import Dict

import requests

from komodo.package_version import (
    LATEST_PACKAGE_ALIAS,
    latest_pypi_version,
    strip_version,
)
from komodo.shell import run, run_env

flatten = itr.chain.from_iterable


def dfs(pkg, version, pkgs, repo):
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
    pkg,
    ver,
    path,
    data,
    prefix,
    builddir,
    makeopts,
    jobs,
    *args,
    cmake="cmake",
    **kwargs,
):
    bdir = f"{pkg}-{ver}-build"
    if builddir is not None:
        bdir = os.path.join(builddir, bdir)

    fakeroot = kwargs["fakeroot"]
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
    if var := kwargs.get("ld_lib_path"):
        setenv["LD_LIBRARY_PATH"] = var
    if var := kwargs.get("binpath"):
        setenv["PATH"] = var

    print(f"Installing {pkg} ({ver}) from source with cmake")
    with run_env(setenv=setenv, cwd=bdir) as run:
        run(cmake, path, *flags, makeopts)
        print(run("make", f"-j{jobs}"))
        print(run("make", f"DESTDIR={fakeroot}", "install"))


def sh(pkg, ver, pkgpath, data, prefix, makefile, *args, **kwargs):
    makefile = data.get(makefile)

    cmd = [
        "bash",
        makefile,
        "--prefix",
        prefix,
        "--fakeroot",
        kwargs["fakeroot"],
        "--python",
        prefix + "/bin/python",
        "--pythonpath",
        kwargs["pythonpath"],
        "--binpath",
        kwargs["binpath"],
        "--pip",
        kwargs["pip"],
        "--virtualenv",
        kwargs["virtualenv"],
        "--ld-library-path",
        kwargs["ld_lib_path"],
    ]
    if (jobs := kwargs.get("jobs")) is not None:
        cmd.extend(["--jobs", jobs])
    if (cmake := kwargs.get("cmake")) is not None:
        cmd.extend(["--cmake", cmake])
    cmd.extend(kwargs["makeopts"].split())

    print(f"Installing {pkg} ({ver}) from sh")
    run(*cmd, cwd=prefix)


def rsync(pkg, ver, pkgpath, data, prefix, *args, **kwargs):
    print(f"Installing {pkg} ({ver}) with rsync")
    # assume a root-like layout in the pkgpath dir, and just copy it
    run(
        "rsync",
        "-am",
        kwargs.get("makeopts"),
        f"{pkgpath}/",
        kwargs["fakeroot"] + prefix,
    )


def download(pkg, ver, pkgpath, data, prefix, *args, **kwargs):
    print(f"Installing {pkg} ({ver}) with download")

    url = kwargs["url"]
    if not url.startswith("https"):
        msg = f"{url} does not use https:// protocol"
        raise ValueError(msg)

    hash_type, hash_value = kwargs["hash"].split(":")
    if hash_type != "sha256":
        msg = f"Hash type {hash_type} given - only sha256 implemented"
        raise NotImplementedError(
            msg,
        )

    fakeprefix = pathlib.Path(kwargs["fakeroot"] + prefix)
    dest_path = fakeprefix / kwargs["destination"]

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


def pip_install(pkg, ver, pkgpath, data, prefix, dlprefix, *args, pip="pip", **kwargs):
    ver = strip_version(ver)
    if ver == LATEST_PACKAGE_ALIAS:
        ver = latest_pypi_version(pkg)
    cmd = [
        pip,
        "install",
        f"{pkg}=={strip_version(ver)}",
        "--root",
        kwargs["fakeroot"],
        "--prefix",
        prefix,
        "--no-index",
        "--no-deps",
        "--ignore-installed",
    ]
    if dlprefix:
        cmd.extend(["--cache-dir", dlprefix, "--find-links", dlprefix])
    if makeopts := kwargs.get("makeopts"):
        cmd.append(makeopts)

    print(f"Installing {pkg} ({ver}) from pip")
    run(*cmd)


def noop(pkg, ver, *args, **kwargs):
    print(f"Doing nothing for noop package {pkg} ({ver})")


def pypaths(prefix, version):
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
    pkgs,
    repo,
    data,
    prefix,
    dlprefix=None,
    builddir=None,
    jobs=1,
    cmk="cmake",
    pip="pip",
    virtualenv=None,
    fakeroot=".",
):
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

    def resolve(x):
        return x.replace("$(prefix)", prefix)

    build = {
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

        current["makeopts"] = resolve(current.get("makeopts", ""))
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
            hash=current.get("hash"),
        )
