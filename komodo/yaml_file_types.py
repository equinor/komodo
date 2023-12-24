import argparse
import os
from collections import namedtuple
from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

komodo_error = namedtuple(
    "KomodoError",
    ["package", "version", "maintainer", "depends", "err"],
)
report = namedtuple(
    "LintReport",
    ["release_name", "maintainers", "dependencies", "versions"],
)


class KomodoException(Exception):
    def __init__(self, error_message: komodo_error) -> None:
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
        package=package,
        version=version,
        maintainer=maintainer,
        err=err,
    )


def load_yaml_from_string(value: str) -> dict:
    try:
        return YAML().load(value)
    except DuplicateKeyError as e:
        raise SystemExit(e) from None


class YamlFile(argparse.FileType):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("r", *args, **kwargs)

    def __call__(self, value):
        file_handle = super().__call__(value)
        yml = load_yaml_from_string(file_handle)
        file_handle.close()
        return yml


class ReleaseFile(YamlFile):
    """Return the data from 'release' YAML file, but validate it first."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.content: dict = None

    def __call__(self, value: str):
        yml: dict = super().__call__(value)
        self.validate_release_file(yml)
        self.content: dict = yml
        return self

    def from_yaml_string(self, value: bytes):
        yml = load_yaml_from_string(value)
        self.validate_release_file(yml)
        self.content: dict = yml
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
            error = Package.validate_package_entry_with_errors(
                package_name,
                package_version,
            )
            errors.extend(error)
        handle_validation_errors(errors, message)

    @staticmethod
    def lint_release_name(packagefile_path: str) -> List[komodo_error]:
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
                ),
            ]

        return []


class ReleaseDir:
    def __call__(self, value: str) -> Dict[str, YamlFile]:
        if not os.path.isdir(value):
            raise NotADirectoryError(value)
        result = {}
        for yaml_file in Path(value).glob("*.yml"):
            result[yaml_file.name.replace(".yml", "")] = ReleaseFile()(
                yaml_file
            ).content
        return result


class ManifestFile(YamlFile):
    """Return the data from 'manifest' YAML, but validate it first."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.content: dict = None

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
                    f"Invalid version type in metadata for package '{package_name}'",
                )
        handle_validation_errors(errors, message)


class RepositoryFile(YamlFile):
    """Return the data from 'repository' YAML, but validate it first."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.content: dict = None

    def __call__(self, value: str):
        self.content: dict = super().__call__(value)
        self.validate_repository_file()
        return self

    def from_yaml_string(self, value: bytes):
        yml = load_yaml_from_string(value)
        self.content: dict = yml
        self.validate_repository_file()
        return self

    def validate_package_entry(
        self,
        package_name: str,
        package_version: str,
    ) -> komodo_error:
        repository_entries = self.content
        if package_name not in repository_entries:
            for real_packagename in [
                lowercase_pkg
                for lowercase_pkg in repository_entries
                if lowercase_pkg.lower() == package_name.lower()
            ]:
                msg = f"Package '{package_name}' not found in repository. Did you mean '{real_packagename}'?"
                raise KomodoException(
                    msg,
                )
            msg = f"Package '{package_name}' not found in repository"
            raise KomodoException(msg)
        if package_version not in repository_entries[package_name]:
            if f"v{package_version}" in repository_entries[package_name]:
                msg = f"Version '{package_version}' of package '{package_name}' not found in repository. Did you mean 'v{package_version}'?"
                raise KomodoException(
                    msg,
                )
            msg = f"Version '{package_version}' of package '{package_name}' not found in repository. Did you mean '{next(iter(repository_entries[package_name].keys()))}'?"
            raise KomodoException(
                msg,
            )

    def lint_maintainer(self, package, version) -> komodo_error:
        repository_entries = self.content
        try:
            self.validate_package_entry(package, version)
        except KomodoException as e:
            raise KomodoException(
                _komodo_error(package=package, version=version, err=e),
            ) from e
        return _komodo_error(
            package=package,
            version=version,
            maintainer=repository_entries[package][version]["maintainer"],
        )

    def validate_repository_file(self) -> None:
        repository_file_content: dict = self.content
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
                        f" correctly ({versions})",
                    )
                    continue
                validation_errors = self.validate_versions(package_name, versions)
                if validation_errors:
                    errors.extend(validation_errors)
            except (ValueError, TypeError) as e:
                errors.append(str(e))

        handle_validation_errors(errors, message)

    def validate_versions(self, package_name: str, versions: dict) -> List[str]:
        """Validates versions-dictionary of a package and returns a list of error messages."""
        errors = []
        for version, version_metadata in versions.items():
            Package.validate_package_version(package_name, version)
            make_errors = Package.validate_package_make_with_errors(
                package_name,
                version,
                version_metadata.get("make"),
            )
            errors.extend(make_errors)
            maintainer_errors = Package.validate_package_maintainer_with_errors(
                package_name,
                version,
                version_metadata.get("maintainer"),
            )
            errors.extend(maintainer_errors)
            for (
                package_property,
                package_property_value,
            ) in version_metadata.items():
                validation_errors = self.validate_package_properties(
                    package_name,
                    version,
                    package_property,
                    package_property_value,
                )
                errors.extend(validation_errors)
        return errors

    def validate_package_properties(
        self,
        package_name: str,
        package_version: str,
        package_property: str,
        package_property_value: str,
    ) -> List[str]:
        """Validates package properties of the specified package
        and returns a list of error messages.
        """
        pre_checked_properties = ["make", "maintainer"]
        errors = []
        if package_property in pre_checked_properties:
            return errors
        if package_property == "depends":
            if not isinstance(package_property_value, list):
                errors.append(
                    f"Dependencies for package {package_name} have"
                    f" invalid type {package_property_value}",
                )
                return errors
            for dependency in package_property_value:
                if not isinstance(dependency, str):
                    errors.append(
                        f"Package {package_name} version {package_version} has"
                        f" invalid dependency type({dependency})",
                    )
                    continue
                if dependency not in self.content:
                    errors.append(
                        f"Dependency '{dependency}' not found for"
                        f" package '{package_name}'",
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
        return errors


class UpgradeProposalsFile(YamlFile):
    """Return the data from 'upgrade_proposals' YAML, but validate it first."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.content: dict = None

    def __call__(self, value: str) -> Dict[str, Dict[str, str]]:
        yml = super().__call__(value)
        self.validate_upgrade_proposals_file(yml)
        self.content: dict = yml
        return self

    def from_yaml_string(self, value):
        yml = load_yaml_from_string(value)
        self.validate_upgrade_proposals_file(yml)
        self.content: dict = yml
        return self

    def validate_upgrade_key(self, upgrade_key: str) -> None:
        assert (
            upgrade_key in self.content
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
                    f"Release version ({release_version}) is not of type string",
                )
                continue
            if packages_to_upgrade is None:
                continue
            if not isinstance(packages_to_upgrade, dict):
                errors.append(
                    "New package upgrades have to be listed in dictionary format"
                    f" ({packages_to_upgrade})",
                )
                continue
            for package_name, package_version in packages_to_upgrade.items():
                errors.extend(
                    Package.validate_package_entry_with_errors(
                        package_name,
                        package_version,
                    ),
                )
        handle_validation_errors(errors, message)


class PackageStatusFile(YamlFile):
    """Return the data from 'package_status' YAML, but validate it first."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.content: dict = None

    def __call__(self, value: str):
        yml = super().__call__(value)
        self.content: dict = yml
        self.validate_package_status_file()
        return self

    def from_yaml_string(self, value: str):
        yml = load_yaml_from_string(value)
        self.content: dict = yml
        self.validate_package_status_file()
        return self

    def validate_package_status_file(self) -> None:
        package_status = self.content
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
                    package_name,
                    status.get("visibility"),
                )
            except (ValueError, TypeError) as e:
                errors.append(str(e))
                continue
            visibility = status["visibility"]
            if visibility == "public":
                maturity_errors = Package.validate_package_maturity_with_errors(
                    package_name,
                    status.get("maturity"),
                )
                errors.extend(maturity_errors)

                importance_errors = Package.validate_package_importance_with_errors(
                    package_name,
                    status.get("importance"),
                )
                errors.extend(importance_errors)

        handle_validation_errors(errors, message)


class Package:
    VALID_VISIBILITIES = ["public", "private"]
    VALID_IMPORTANCES = ["low", "medium", "high"]
    VALID_MATURITIES = ["experimental", "stable", "deprecated"]
    VALID_MAKES = ["cmake", "sh", "pip", "rsync", "noop", "download"]

    @staticmethod
    def validate_package_name(package_name: str) -> None:
        if isinstance(package_name, str):
            return
        msg = f"Package name ({package_name}) should be of type string"
        raise TypeError(msg)

    @staticmethod
    def validate_package_version(package_name: str, package_version: str) -> None:
        if isinstance(package_version, str):
            return
        msg = f"Package '{package_name}' has invalid version type ({package_version})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_entry(package_name: str, package_version) -> None:
        Package.validate_package_name(package_name)
        Package.validate_package_version(package_name, package_version)

    @staticmethod
    def validate_package_entry_with_errors(
        package_name: str,
        package_version: str,
    ) -> List[str]:
        """Validates package name and version, and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_entry(package_name, package_version)
        except (ValueError, TypeError) as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_importance(package_name: str, package_importance: str) -> None:
        if isinstance(package_importance, str):
            if package_importance in Package.VALID_IMPORTANCES:
                return
            msg = f"{package_name} has invalid importance value ({package_importance})"
            raise ValueError(
                msg,
            )
        msg = f"{package_name} has invalid importance type ({package_importance})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_importance_with_errors(
        package_name,
        package_importance: str,
    ) -> List[str]:
        """Validates package importance of a package and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_importance(package_name, package_importance)
        except (ValueError, TypeError) as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_visibility(package_name: str, package_visibility: str) -> None:
        if isinstance(package_visibility, str):
            if package_visibility in Package.VALID_VISIBILITIES:
                return
            msg = f"Package '{package_name}' has invalid visibility value ({package_visibility})"
            raise ValueError(
                msg,
            )
        msg = f"Package '{package_name}' has invalid visibility type ({package_visibility})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_maturity(package_name: str, package_maturity: str) -> None:
        if isinstance(package_maturity, str):
            if package_maturity in Package.VALID_MATURITIES:
                return
            msg = f"Package '{package_name}' has invalid maturity value ({package_maturity})"
            raise ValueError(
                msg,
            )
        msg = f"Package '{package_name}' has invalid maturity type ({package_maturity})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_maturity_with_errors(
        package_name: str,
        package_maturity: str,
    ) -> List[str]:
        """Validates package maturity of a package and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_maturity(package_name, package_maturity)
        except (ValueError, TypeError) as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_make(
        package_name: str,
        package_version: str,
        package_make: str,
    ) -> None:
        if isinstance(package_make, str):
            if package_make in Package.VALID_MAKES:
                return
            msg = f"Package '{package_name}' version {package_version} has invalid make value ({package_make})"
            raise ValueError(
                msg,
            )
        msg = f"Package '{package_name}' version {package_version} has invalid make type ({package_make})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_make_with_errors(
        package_name: str,
        package_version: str,
        package_make: str,
    ) -> List[str]:
        """Validates make of a package and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_make(package_name, package_version, package_make)
        except (ValueError, TypeError) as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_maintainer(
        package_name: str,
        package_version: str,
        package_maintainer: str,
    ) -> None:
        if isinstance(package_maintainer, str):
            return
        msg = f"Package '{package_name}' version {package_version} has invalid maintainer type ({package_maintainer})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_maintainer_with_errors(
        package_name: str,
        package_version: str,
        package_maintainer: str,
    ) -> List[str]:
        """Validates maintainer of a package and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_maintainer(
                package_name,
                package_version,
                package_maintainer,
            )
        except TypeError as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_source(
        package_name: str,
        package_version: str,
        package_source: str,
    ) -> None:
        if isinstance(package_source, (str, type(None))):
            return
        msg = f"Package '{package_name}' version {package_version} has invalid source type ({package_source})"
        raise TypeError(
            msg,
        )

    @staticmethod
    def validate_package_source_with_errors(
        package_name: str,
        package_version: str,
        package_source: str,
    ) -> List[str]:
        """Validates source of a package and returns a list of error messages."""
        errors = []
        try:
            Package.validate_package_source(
                package_name,
                package_version,
                package_source,
            )
        except TypeError as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def validate_package_property_type(
        package_name: str,
        package_version: str,
        package_property: str,
        package_property_value: str,
    ):
        if not isinstance(package_property, str):
            msg = f"Package '{package_name}' version has invalid property type ({package_property})"
            raise TypeError(
                msg,
            )
        if not isinstance(package_property_value, str):
            msg = f"Package '{package_name}' version '{package_version}' property '{package_property}' has invalid property value type ({package_property_value})"
            raise TypeError(
                msg,
            )


def handle_validation_errors(errors: List[str], message: str):
    if errors:
        raise SystemExit("\n".join([*errors, message]))


def load_package_status_file(package_status_string: str):
    return PackageStatusFile().from_yaml_string(package_status_string)


def load_repository_file(repository_file_string):
    return RepositoryFile().from_yaml_string(repository_file_string)
