import argparse
import os
from collections import namedtuple
from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

komodo_error = namedtuple(
    "KomodoError", ["package", "version", "maintainer", "depends", "err"]
)
report = namedtuple(
    "LintReport", ["release_name", "maintainers", "dependencies", "versions"]
)


class KomodoException(Exception):
    def __init__(self, error_message: komodo_error):
        self.error = error_message


MISSING_PACKAGE = "missing package"
MISSING_VERSION = "missing version"
MISSING_DEPENDENCY = "missing dependency"
MISSING_MAINTAINER = "missing maintainer"
MISSING_MAKE = "missing make information"
MALFORMED_VERSION = "malformed version"
MAIN_VERSION = "dangerous version (main branch)"
MASTER_VERSION = "dangerous version (master branch)"
FLOAT_VERSION = "dangerous version (float interpretable)"


def _komodo_error(package=None, version=None, maintainer=None, depends=None, err=None):
    return komodo_error(
        package=package,
        version=version,
        maintainer=maintainer,
        depends=depends,
        err=err,
    )


def __reg_version_err(errs, package, version, maintainer, err=MALFORMED_VERSION):
    return _komodo_error(
        package=package, version=version, maintainer=maintainer, err=err
    )


class YamlFile(argparse.FileType):
    def __init__(self, *args, **kwargs):
        super().__init__("r", *args, **kwargs)

    def __call__(self, value):
        file_handle = super().__call__(value)
        yaml = YAML()
        yml = yaml.load(file_handle)
        file_handle.close()
        return yml


class ReleaseFile(YamlFile):
    """
    Return the data from 'release' YAML file, but validate it first.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yml = None

    def __call__(self, value: str):
        yml: dict = super().__call__(value)
        self.validate_release_file(yml)
        self.yml = yml
        return self

    def from_yaml_string(self, value: bytes):
        yaml = YAML()
        yml: dict = yaml.load(value)
        self.validate_release_file(yml)
        self.yml = yml
        return self

    @staticmethod
    def validate_release_file(release_file_content: dict) -> None:
        message = (
            "The file you provided does not appear to be a release file "
            "produced by komodo. It may be a repository file. Release files "
            "have a format like the following:\n\n"
            'python: 3.8.6-builtin\nsetuptools: 68.0.0\nwheel: 0.40.0\nzopfli: "0.3"'
        )
        assert isinstance(release_file_content, dict), message
        errors = []
        for package_name, package_version in release_file_content.items():
            Package.validate_package_entry_with_errors(
                package_name, package_version, errors
            )
        handle_validation_errors(errors, message)

    @staticmethod
    def lint_release_name(packagefile_path: str):
        relname = os.path.basename(packagefile_path)
        found = False
        for py_suffix in "-py27", "-py36", "-py38", "-py310":
            for rh_suffix in "", "-rhel6", "-rhel7", "-rhel8":
                if relname.endswith(py_suffix + rh_suffix + ".yml"):
                    found = True
                    break
        if not found:
            return [
                _komodo_error(
                    package=packagefile_path,
                    err=(
                        "Invalid release name suffix. "
                        "Must be of the form -pyXX[X] or -pyXX[X]-rhelY"
                    ),
                )
            ]

        return []


class ReleaseDir:
    def __call__(self, value: str) -> Dict[str, YamlFile]:
        if not os.path.isdir(value):
            raise NotADirectoryError(value)
        result = {}
        for yaml_file in Path(value).glob("*.yaml"):
            result.update(ReleaseFile()(yaml_file))
        return result


class ManifestFile(YamlFile):
    """
    Return the data from 'manifest' YAML, but validate it first.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yml = None

    def __call__(self, value: str) -> Dict[str, Dict[str, str]]:
        yml = super().__call__(value)
        self.validate_manifest_file(yml)
        return yml

    @staticmethod
    def validate_manifest_file(manifest_file_content: dict):
        message = (
            "The file you provided does not appear to be a manifest file "
            "produced by komodo. It may be a release file. Manifest files "
            "have a format like the following:\n\n"
            "python:\n  maintainer: foo@example.com\n  version: 3-builtin\n"
            "treelib:\n  maintainer: foo@example.com\n  version: 1.6.1\n"
        )
        assert isinstance(manifest_file_content, dict), message
        errors = []
        for package_name, metadata in manifest_file_content.items():
            if not isinstance(metadata, dict):
                errors.append(f"Invalid metadata for package '{package_name}'")
                continue
            if not isinstance(metadata["version"], str):
                errors.append(
                    f"Invalid version type in metadata for package '{package_name}'"
                )
        handle_validation_errors(errors, message)


class RepositoryFile(YamlFile):
    """
    Return the data from 'repository' YAML, but validate it first.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yml = None

    def __call__(self, value: str):
        self.yml = super().__call__(value)
        self.validate_repository_file()
        return self

    def from_yaml_string(self, value: bytes):
        yaml = YAML()
        yml = yaml.load(value)
        self.yml = yml
        self.validate_repository_file()
        return self

    def validate_package_entry(
        self, package_name: str, package_version: str
    ) -> komodo_error:
        repository_entries = self.yml
        if package_name not in repository_entries:
            raise KomodoException(f"Package '{package_name}' not found in repository")
        if package_version not in repository_entries[package_name]:
            raise KomodoException(
                f"Version '{package_version}' of package '{package_name}' not found in"
                " repository"
            )

    def lint_maintainer(self, package, version) -> komodo_error:
        repository_entries = self.yml
        if package not in repository_entries:
            raise KomodoException(_komodo_error(package=package, err=MISSING_PACKAGE))
        if version not in repository_entries[package]:
            raise KomodoException(
                _komodo_error(package=package, version=version, err=MISSING_VERSION)
            )
        return _komodo_error(
            package=package,
            version=version,
            maintainer=repository_entries[package][version]["maintainer"],
        )

    def validate_repository_file(self) -> None:
        repository_file_content: dict = self.yml
        message = (
            "The file you provided does not appear to be a repository file "
            "produced by komodo. It may be a release file. Repository files "
            "have a format like the following:\n\n"
            "pytest-runner:\n  6.0.0:\n    make: pip\n    "
            "maintainer: scout\n    depends:\n      - wheel\n      - "
            """setuptools\n      - python\n\npython:\n  "3.8":\n    ..."""
        )
        assert isinstance(repository_file_content, dict), message
        errors = []
        for package_name, versions in repository_file_content.items():
            try:
                Package.validate_package_name(package_name)
                if not isinstance(versions, dict):
                    errors.append(
                        f"Versions of package '{package_name}' is not formatted"
                        f" correctly ({versions})"
                    )
                    continue
                self.validate_versions(package_name, versions, errors)

            except (ValueError, TypeError) as e:
                errors.append(str(e))
                continue

        handle_validation_errors(errors, message)

    def validate_versions(self, package_name: str, versions: dict, errors):
        for version, version_metadata in versions.items():
            Package.validate_package_version(package_name, version)
            Package.validate_package_make_with_errors(
                package_name, version, version_metadata.get("make"), errors
            )
            Package.validate_package_maintainer_with_errors(
                package_name,
                version,
                version_metadata.get("maintainer"),
                errors,
            )
            for (
                package_property,
                package_property_value,
            ) in version_metadata.items():
                self.validate_package_properties(
                    package_name,
                    version,
                    package_property,
                    package_property_value,
                    errors,
                )

    def validate_package_properties(
        self,
        package_name: str,
        package_version: str,
        package_property: str,
        package_property_value: str,
        errors: List[str],
    ):
        PRE_CHECKED_PROPERTIES = ["make", "maintainer"]
        if package_property in PRE_CHECKED_PROPERTIES:
            return
        if package_property == "depends":
            if not isinstance(package_property_value, list):
                errors.append(
                    f"Dependencies for package {package_name} has"
                    f" invalid type {package_property_value}"
                )
                return
            for dependency in package_property_value:
                if not isinstance(dependency, str):
                    errors.append(
                        f"Package {package_name} version {package_version} has"
                        f" invalid dependency type({dependency})"
                    )
                    continue
                if dependency not in self.yml.keys():
                    errors.append(
                        f"Dependency '{dependency}' not found for"
                        f" package '{package_name}'"
                    )
        else:
            try:
                Package.validate_package_property_type(
                    package_name,
                    package_version,
                    package_property,
                    package_property_value,
                )
            except (ValueError, TypeError) as e:
                errors.append(str(e))


class UpgradeProposalsFile(YamlFile):
    """
    Return the data from 'upgrade_proposals' YAML, but validate it first.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yml = None

    def __call__(self, value: str) -> Dict[str, Dict[str, str]]:
        yml = super().__call__(value)
        self.validate_upgrade_proposals_file(yml)
        self.yml = yml
        return self

    def from_yaml_string(self, value):
        yaml = YAML()
        yml = yaml.load(value)
        self.validate_upgrade_proposals_file(yml)
        self.yml = yml
        return self

    def validate_upgrade_key(self, upgrade_key: str) -> None:
        assert (
            upgrade_key in self.yml
        ), f"No section for this release ({upgrade_key}) in upgrade_proposals.yml"

    @staticmethod
    def validate_upgrade_proposals_file(upgrade_proposals_file_content: dict) -> None:
        message = (
            "The file you provided does not appear to be an upgrade_proposals file"
            " produced by komodo. It may be a release file. Upgrade_proposals files"
            ' have a format like the following:\n2022-08:\n2022-09:\n  python: "3.9"\n'
            '  zopfli: "0.3"\n  libecalc: 8.2.9'
        )
        errors = []
        assert isinstance(upgrade_proposals_file_content, dict), message
        for (
            release_version,
            packages_to_upgrade,
        ) in upgrade_proposals_file_content.items():
            if not isinstance(release_version, str):
                errors.append(
                    f"Release version ({release_version}) is not of type string"
                )
                continue
            if packages_to_upgrade is None:
                continue
            if not isinstance(packages_to_upgrade, dict):
                errors.append(
                    "New package upgrades have to be listed in dictionary format"
                    f" ({packages_to_upgrade})"
                )
                continue
            for package_name, package_version in packages_to_upgrade.items():
                Package.validate_package_entry_with_errors(
                    package_name, package_version, errors
                )
        handle_validation_errors(errors, message)


class PackageStatusFile(YamlFile):
    """
    Return the data from 'package_status' YAML, but validate it first.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yml = None

    def __call__(self, value: str):
        yml = super().__call__(value)
        self.yml = yml
        self.validate_package_status_file()
        return self

    def from_yaml_string(self, value: str):
        yaml = YAML()
        yml = yaml.load(value)
        self.yml = yml
        self.validate_package_status_file()
        return self

    def validate_package_status_file(self) -> None:
        package_status = self.yml
        message = (
            "The file you provided does not appear to be a package_status file"
            " produced by komodo. It may be a release file. Package_status files have"
            " a format like the following:\n\nzopfli:\n  visibility:"
            " private\npython:\n  visibility: public\n  maturity: stable\n "
            " importance: high"
        )

        assert isinstance(package_status, dict), message

        errors = []
        for package_name, status in package_status.items():
            try:
                Package.validate_package_name(package_name)
                if not isinstance(status, dict):
                    errors.append(f"Invalid package data for {package_name} - {status}")
                    continue
                Package.validate_package_visibility(
                    package_name, status.get("visibility")
                )
            except (ValueError, TypeError) as e:
                errors.append(str(e))
                continue
            visibility = status["visibility"]
            if visibility == "public":
                Package.validate_package_maturity_with_errors(
                    package_name, status.get("maturity"), error_list=errors
                )
                Package.validate_package_importance_with_errors(
                    package_name, status.get("importance"), error_list=errors
                )

        handle_validation_errors(errors, message)


class Package:
    VALID_VISIBILITIES = ["public", "private"]
    VALID_IMPORTANCES = ["low", "medium", "high"]
    VALID_MATURITIES = ["experimental", "stable", "deprecated"]
    VALID_MAKES = ["rpm", "cmake", "sh", "pip", "rsync", "noop", "download"]

    @staticmethod
    def validate_package_name(package_name: str) -> bool:
        if isinstance(package_name, str):
            if str.islower(package_name):
                return True
            raise ValueError(f"Package name '{package_name}' should be lowercase.")
        raise TypeError(f"Package name ({package_name}) should be of type string")

    @staticmethod
    def validate_package_version(package_name: str, package_version: str) -> bool:
        if isinstance(package_version, str):
            return True
        raise TypeError(
            f"Package '{package_name}' has invalid version type ({package_version})"
        )

    @staticmethod
    def validate_package_entry(package_name: str, package_version) -> bool:
        Package.validate_package_name(package_name)
        Package.validate_package_version(package_name, package_version)

    @staticmethod
    def validate_package_entry_with_errors(
        package_name: str, package_version: str, error_list: List[str]
    ) -> None:
        try:
            Package.validate_package_entry(package_name, package_version)
        except (ValueError, TypeError) as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_importance(package_name: str, package_importance: str) -> bool:
        if isinstance(package_importance, str):
            if package_importance in Package.VALID_IMPORTANCES:
                return True
            raise ValueError(
                f"{package_name} has invalid importance value ({package_importance})"
            )
        raise TypeError(
            f"{package_name} has invalid importance type ({package_importance})"
        )

    @staticmethod
    def validate_package_importance_with_errors(
        package_name, package_importance: str, error_list: List[str]
    ) -> None:
        try:
            Package.validate_package_importance(package_name, package_importance)
        except (ValueError, TypeError) as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_visibility(package_name: str, package_visibility: str) -> None:
        if isinstance(package_visibility, str):
            if package_visibility in Package.VALID_VISIBILITIES:
                return True
            raise ValueError(
                f"Package '{package_name}' has invalid visibility value"
                f" ({package_visibility})"
            )
        raise TypeError(
            f"Package '{package_name}' has invalid visibility type"
            f" ({package_visibility})"
        )

    @staticmethod
    def validate_package_maturity(package_name: str, package_maturity: str) -> bool:
        if isinstance(package_maturity, str):
            if package_maturity in Package.VALID_MATURITIES:
                return True
            raise ValueError(
                f"Package '{package_name}' has invalid maturity value"
                f" ({package_maturity})"
            )
        raise TypeError(
            f"Package '{package_name}' has invalid maturity type ({package_maturity})"
        )

    @staticmethod
    def validate_package_maturity_with_errors(
        package_name: str, package_maturity: str, error_list: List[str]
    ) -> None:
        try:
            Package.validate_package_maturity(package_name, package_maturity)
        except (ValueError, TypeError) as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_make(
        package_name: str, package_version: str, package_make: str
    ) -> bool:
        if isinstance(package_make, str):
            if package_make in Package.VALID_MAKES:
                return True
            raise ValueError(
                f"Package '{package_name}' version {package_version} has invalid make "
                f"value ({package_make})"
            )
        raise TypeError(
            f"Package '{package_name}' version {package_version} has invalid make type"
            f" ({package_make})"
        )

    @staticmethod
    def validate_package_make_with_errors(
        package_name: str,
        package_version: str,
        package_make: str,
        error_list: List[str],
    ) -> None:
        try:
            Package.validate_package_make(package_name, package_version, package_make)
        except (ValueError, TypeError) as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_maintainer(
        package_name: str, package_version: str, package_maintainer: str
    ) -> bool:
        if isinstance(package_maintainer, str):
            return True
        raise TypeError(
            f"Package '{package_name}' version {package_version} has invalid"
            f" maintainer type ({package_maintainer})"
        )

    @staticmethod
    def validate_package_maintainer_with_errors(
        package_name: str,
        package_version: str,
        package_maintainer: str,
        error_list: List[str],
    ) -> None:
        try:
            Package.validate_package_maintainer(
                package_name, package_version, package_maintainer
            )
        except TypeError as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_source(
        package_name: str, package_version: str, package_source: str
    ) -> bool:
        if isinstance(package_source, (str, type(None))):
            return True
        raise TypeError(
            f"Package '{package_name}' version {package_version} has invalid source"
            f" type ({package_source})"
        )

    @staticmethod
    def validate_package_source_with_errors(
        package_name: str,
        package_version: str,
        package_source: str,
        error_list: List[str],
    ) -> None:
        try:
            Package.validate_package_source(
                package_name, package_version, package_source
            )
        except TypeError as e:
            error_list.append(str(e))

    @staticmethod
    def validate_package_property_type(
        package_name: str,
        package_version: str,
        package_property: str,
        package_property_value: str,
    ):
        if isinstance(package_property, str):
            if not package_property.islower():
                raise ValueError(
                    f"Package '{package_name}' version '{package_version}' property"
                    f" should be lowercase ({package_property})"
                )
        else:
            raise TypeError(
                f"Package '{package_name}' version has invalid property type"
                f" ({package_property})"
            )
        if not isinstance(package_property_value, str):
            raise TypeError(
                f"Package '{package_name}' version '{package_version}' property"
                f" '{package_property}' has invalid property value type"
                f" ({package_property_value})"
            )


def handle_validation_errors(errors: List[str], message: str):
    if errors:
        raise SystemExit("\n".join(errors + [message]))


def load_package_status_file(package_status_string: str):
    package_status = PackageStatusFile().from_yaml_string(package_status_string)
    return package_status


def load_repository_file(repository_file_string):
    repository_file = RepositoryFile().from_yaml_string(repository_file_string)
    return repository_file
