import os
import platform
import subprocess
import sys
from typing import Dict, List, Set, Tuple

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion

from .package_version import LATEST_PACKAGE_ALIAS
from .shell import shell


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


# pylint: disable=too-many-instance-attributes
class PypiDependencies:
    def __init__(
        self,
        to_install: Dict[str, str],
        python_version: str,
        cachefile: str = "./pypi_dependencies.yml",
        venv="./dependencies_venv",
    ) -> None:
        environment["python_version"] = python_version
        self.satisfied_requirements = set()
        self.failed_requirements = set()
        self.used_packages = set()

        self._to_install = to_install

        self._install_names = {canonicalize_name(name): name for name in to_install}
        self._to_install = {
            canonicalize_name(name): version for name, version in to_install.items()
        }
        self._cachefile = cachefile
        self._venv = venv
        if os.path.exists(self._cachefile):
            with open(self._cachefile, "r", encoding="utf-8") as f:
                self.requirements = yaml.safe_load(f)
                self.requirements = {
                    canonicalize_name(name): r for name, r in self.requirements.items()
                }
        else:
            self.requirements = {}

        if not os.path.exists(self._venv):
            shell(f"python -m venv {self._venv}")
        shell(f"env VIRTUAL_ENV={venv} {venv}/bin/python -m pip install setuptools")
        shell(f"env VIRTUAL_ENV={venv} {venv}/bin/python -m pip install packaging")

        self._user_specified = {}

    def check(self, packages=None):
        for package_name, version in packages or self._to_install.items():
            requirements = self.get_requirements(package_name, version)
            self.used_packages.add(package_name)
            for r in requirements:
                _ = self.satisfied(r)

    def add_user_specified(
        self,
        package_name: str,
        depends: List[str],
    ) -> None:
        canonical = canonicalize_name(package_name)
        # It is necessary to set the version to the installed
        # version if present as the version check considers
        # beta versions as failing unless specifically specified
        self._user_specified[canonicalize_name(package_name)] = [
            Requirement(
                d
                if self._to_install.get(canonicalize_name(d))
                in [None, LATEST_PACKAGE_ALIAS, "main", "master"]
                else f"{d}=={self._to_install.get(canonicalize_name(d))}"
            )
            for d in depends
            if d != "python"
        ]
        self._install_names[canonical] = package_name

    def dump_cache(self):
        with open(self._cachefile, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.requirements, f)

    def get_requirements(
        self, package_name: str, package_version: str
    ) -> List[Requirement]:
        canonical = canonicalize_name(package_name)
        if canonical in self._user_specified:
            return self._user_specified[canonical]

        if canonical not in self.requirements:
            self.requirements[canonical] = {}

        if package_version not in self.requirements[canonical]:
            try:
                if package_version == LATEST_PACKAGE_ALIAS:
                    subprocess.check_output(
                        (
                            f"env VIRTUAL_ENV={self._venv} {self._venv}/bin/python -m "
                            f"pip install {package_name} --no-deps"
                        ).split()
                    )
                else:
                    subprocess.check_output(
                        (
                            f"env VIRTUAL_ENV={self._venv} {self._venv}/bin/python -m "
                            f"pip install {package_name}=={package_version} --no-deps"
                        ).split()
                    )
            except Exception as err:
                raise ValueError(
                    f"Could not install {package_name} {package_version} from pypi"
                    f"With python version {platform.python_version()} "
                    "in order to determine dependencies."
                    "This may be because no wheel exists for this python version."
                    "In order to resolve the problem you can run the dependency check "
                    f"locally and add it {self._cachefile}."
                ) from err
            result = subprocess.run(
                [
                    f"{self._venv}/bin/python",
                    "-c",
                    "from importlib.metadata import requires;"
                    'print("\\n".join(r.replace("\\n", " ")'
                    f' for r in (requires("{package_name}") or [])), end="");',
                ],
                env={"VIRTUAL_ENV": self._venv},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            output = result.stdout.decode()

            if not output or output.isspace():
                self.requirements[canonical][package_version] = []
            else:
                self.requirements[canonical][package_version] = output.split("\n")

        return [Requirement(r) for r in self.requirements[canonical][package_version]]

    def _make_install_name(self, name: str) -> str:
        canonical = canonicalize_name(name)
        return self._install_names.get(canonical, canonical)

    def _version_satisfied(self, version: str, requirement: Requirement) -> bool:
        if version in ["main", "master", LATEST_PACKAGE_ALIAS]:
            return True
        try:
            return version in requirement.specifier
        except InvalidVersion:
            return True

    def _is_necessary(self, requirement, extras):
        environment["extra"] = ",".join(extras)
        return requirement.marker is None or requirement.marker.evaluate(environment)

    def _satisfied(
        self,
        requirements: List[Requirement],
    ) -> Tuple[bool, List[Tuple[List[Requirement], Set[str]]]]:
        installed = self._to_install
        also = []
        for r in requirements:
            name = canonicalize_name(r.name)
            if name not in installed:
                print(f"Not installed: {name}")
                return False, []
            self.used_packages.add(self._install_names[name])
            installed_version = installed[name]

            if not self._version_satisfied(installed_version, r):
                return False, []

            also.append((self.get_requirements(r.name, installed_version), r.extras))
        return True, also

    def satisfied(
        self,
        requirement: Requirement,
        extra=None,
    ) -> bool:
        """
        >>> from packaging.requirements import Requirement #doctest:+ELLIPSIS
        >>> PypiDependencies(to_install={}, python_version="3.8").satisfied(
        ... Requirement("PyJWT[crypto] (<3, >=1.0.0)")
        ... )
        [...
        Not installed: pyjwt
        False
        >>> PypiDependencies(to_install={"PyJWT": "2.3.0"}, python_version="3.8").satisfied(
        ...     Requirement("PyJWT[crypto] (<3, >=1.0.0)")
        ... )
        [...
        True
        """
        extra = extra or set()
        if not self._is_necessary(requirement, extra):
            return True
        if requirement in self.failed_requirements:
            return False
        if requirement in self.satisfied_requirements:
            return True

        satisfied, also = self._satisfied([requirement])
        if satisfied:
            self.satisfied_requirements.add(requirement)
        else:
            self.failed_requirements.add(requirement)
        return satisfied and all(
            [self.satisfied(a, extra) for (rs, extra) in also for a in rs]
        )
