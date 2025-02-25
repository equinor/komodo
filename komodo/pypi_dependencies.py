from __future__ import annotations

import os
import platform
import subprocess
import sys
from collections.abc import Iterable
from tempfile import TemporaryDirectory

import pkginfo
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion


# From Pep 508
def format_full_version(info) -> str:
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


environment = {
    "implementation_name": sys.implementation.name,
    "implementation_version": format_full_version(sys.implementation.version),
    "os_name": os.name,
    "platform_machine": platform.machine(),
    "platform_python_implementation": platform.python_implementation(),
    "platform_release": platform.release(),
    "platform_system": platform.system(),
    "platform_version": platform.version(),
    "python_full_version": platform.python_version(),
    "python_version": ".".join(platform.python_version_tuple()[:2]),
    "sys_platform": sys.platform,
}


def version_list_to_requirements(
    version_list: Iterable[tuple[str, str | None, list[str]]],
) -> list[Requirement]:
    return [
        Requirement(
            f"{d}[{','.join(extras)}]"
            if version in [None, "main", "master"]
            else f"{d}[{','.join(extras)}]=={version}"
        )
        for d, version, extras in version_list
        if d != "python"
    ]


class PypiDependencies:
    def __init__(
        self,
        to_install: dict[str, str],
        python_version: str,
        cachefile: str | None = "./pypi_dependencies.yml",
    ) -> None:
        """A dependency checker for pypi packages.

        Args:
            to_install:
                All packages that are to be installed
            python_version:
                the python version string, e.g. 3.8.11
            cachefile:
                filename to use for package metadata fetched from pypi. None means no cache.

        """
        self.python_version = python_version
        environment["python_full_version"] = python_version
        environment["python_version"] = ".".join(python_version.split(".")[0:2])
        self._satisfied_requirements = set()
        self._failed_requirements: dict[Requirement, str] = {}
        self._used_packages = set()

        self._install_names = {canonicalize_name(name): name for name in to_install}
        self._to_install = {
            canonicalize_name(name): version for name, version in to_install.items()
        }
        self._cachefile = cachefile
        if self._cachefile is not None and os.path.exists(self._cachefile):
            with open(self._cachefile, encoding="utf-8") as f:
                self.requirements = yaml.safe_load(f)
                self.requirements = {
                    canonicalize_name(name): r for name, r in self.requirements.items()
                }
        else:
            self.requirements = {}

        self._user_specified = {}

    def failed_requirements(self):
        """lists which requirements were not met.

        Args:
            packages:
                which packages to consider, by default: all.

        >>> pypi_packages = {
        ...    "ert": "11.1.0",
        ...    "aiohttp": "3.10.10",
        ...    "deprecation": "2.1.0",
        ...    "filelock": "3.16.1",
        ...    "jinja2": "3.1.4",
        ...    "aiohappyeyeballs": "2.4.3",
        ...    "cryptography": "43.0.1",
        ...    "PyJWT": "2.3.0"}
        >>> all_packages = {
        ...    **pypi_packages,
        ...    "xtgeo": "main",
        ...    "iterative_ensemble_smoother": "main"}
        >>> dependencies = PypiDependencies(all_packages, python_version="3.8")
        >>> dependencies.add_user_specified("xtgeo", [])
        >>> dependencies.add_user_specified("iterative_ensemble_smoother", [])
        >>> dependencies.failed_requirements() # doctest: +ELLIPSIS
        Not installed: aiosignal...
        """
        for package_name, version in self._to_install.items():
            requirements = self._get_requirements(package_name, version)
            for r in requirements:
                _ = self.satisfied(r, package_name)
        return self._failed_requirements

    def used_packages(self, top_level_requirements: Iterable[Requirement]) -> set[str]:
        """Given you want to install top_level_requirements, returns list of
        all packages that must be installed to satisfy dependencies.

        Args:
            top_level_requirements:
                Requirements that must be satisified
        """
        self._used_packages = set()  # clear packages used
        for requirement in top_level_requirements:
            self._used_packages.add(requirement.name)
            _ = self.satisfied(requirement, requirement.name)
        return self._used_packages

    def add_user_specified(
        self,
        package_name: str,
        depends: list[str],
    ) -> None:
        canonical = canonicalize_name(package_name)
        # It is necessary to set the version to the installed
        # version if present as the version check considers
        # beta versions as failing unless specifically specified
        depends_versions = [
            (name, self._to_install.get(canonicalize_name(name)), [])
            for name in depends
            if name != "python"
        ]
        self._user_specified[canonical] = version_list_to_requirements(depends_versions)
        self._install_names[canonical] = package_name

    def dump_cache(self):
        if self._cachefile is not None:
            with open(self._cachefile, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.requirements, f)

    def _get_requirements(
        self, package_name: str, package_version: str
    ) -> list[Requirement]:
        """

        Returns:
            List of requirements for given package.

        >>> from packaging.requirements import Requirement
        >>> PypiDependencies({}, python_version="3.8.11")._get_requirements(
        ...     "rips",
        ...     "2024.3.0.2"
        ... )
        [<Requirement('grpcio')>, <Requirement('protobuf')>, <Requirement('wheel')>]
        """
        canonical = canonicalize_name(package_name)
        if canonical in self._user_specified:
            return self._user_specified[canonical]

        if canonical not in self.requirements:
            self.requirements[canonical] = {}

        return self._get_requirements_from_pypi(package_name, package_version)

    def _get_requirements_from_pypi(
        self, package_name: str, package_version: str
    ) -> list[Requirement]:
        canonical = canonicalize_name(package_name)
        if package_version not in self.requirements[canonical]:
            with TemporaryDirectory() as tmpdir:
                try:
                    subprocess.check_output(
                        [
                            "pip",
                            "download",
                            f"{package_name}=={package_version}",
                            f"--python-version={self.python_version}",
                            "--no-deps",
                        ],
                        cwd=tmpdir,
                    )
                except Exception as err:
                    raise ValueError(
                        f"Could not install {package_name} {package_version} from pypi "
                        f"With python version {self.python_version} "
                        "in order to determine dependencies. "
                        "This may be because no wheel exists for this python version."
                    ) from err

                files = os.listdir(tmpdir)
                if len(files) != 1:
                    raise ValueError(
                        f"Did not get one wheel for download {package_name}=={package_version}."
                        f"Got: {files}"
                    )
                file = files[0]
                if not file.endswith(".whl"):
                    subprocess.check_output(
                        [
                            "pip",
                            "wheel",
                            "--use-pep517",
                            "--no-verify",
                            "--no-deps",
                            "--disable-pip-version-check",
                            file,
                        ],
                        cwd=tmpdir,
                    )
                    file = [f for f in os.listdir(tmpdir) if f.endswith(".whl")][0]
                dist = pkginfo.Wheel(os.path.join(tmpdir, file))
                self.requirements[canonical][package_version] = dist.requires_dist

        return [Requirement(r) for r in self.requirements[canonical][package_version]]

    def _version_satisfies_requirement(
        self, version: str, requirement: Requirement
    ) -> bool:
        """Whether the requirement is satisfied by the version"""

        if version in ["main", "master"]:
            return True
        try:
            specifier = requirement.specifier
            specifier.prereleases = True
            return version in specifier
        except InvalidVersion:
            return True

    def _is_required_by_environment(
        self, requirement: Requirement, extras: Iterable[str]
    ) -> bool:
        """Is the requirement necessary for the environment"""
        environment["extra"] = ",".join(extras)
        return requirement.marker is None or requirement.marker.evaluate(environment)

    def _satisfied(
        self,
        requirements: list[Requirement],
    ) -> tuple[bool, list[tuple[list[Requirement], set[str]]]]:
        installed = self._to_install
        transient_requirements = []
        for requirement in requirements:
            name = canonicalize_name(requirement.name)
            if name not in installed:
                print(f"Not installed: {name}")
                return False, []
            self._used_packages.add(self._install_names[name])
            installed_version = installed[name]

            if not self._version_satisfies_requirement(installed_version, requirement):
                return False, []

            transient_requirements.append(
                (
                    self._get_requirements(requirement.name, installed_version),
                    requirement.extras,
                )
            )
        return True, transient_requirements

    def satisfied(
        self,
        requirement: Requirement,
        package_name: str = "",
        extra: set[str] | None = None,
    ) -> bool:
        """Is the given requirement satisfied.

        Args:
            package_name:
                The package that has the given requirement.
            extra:
                Optional set of extras for package_name.

        >>> from packaging.requirements import Requirement
        >>> PypiDependencies({}, python_version="3.8").satisfied(
        ... Requirement("PyJWT[crypto] (<3, >=1.0.0)")
        ... )
        Not installed: pyjwt
        False
        >>> packages = {"PyJWT": "2.3.0"}
        >>> PypiDependencies(packages, python_version="3.8").satisfied(
        ...     Requirement("PyJWT (<3, >=1.0.0)")
        ... )
        True
        """
        extra = extra or set()
        if not self._is_required_by_environment(requirement, extra):
            return True
        if requirement in self._failed_requirements:
            return False
        if requirement in self._satisfied_requirements:
            return True

        satisfied, transient_requirements = self._satisfied([requirement])
        if satisfied:
            self._satisfied_requirements.add(requirement)
        elif requirement in self._failed_requirements:
            self._failed_requirements[requirement] += f", {package_name}"
        else:
            self._failed_requirements[requirement] = package_name
        return satisfied and all(
            self.satisfied(transient, package_name, extra)
            for (transients, extra) in transient_requirements
            for transient in transients
        )
