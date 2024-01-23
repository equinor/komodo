#!/usr/bin/env python
import argparse
import configparser
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Union

from ruamel.yaml import YAML

from komodo.yaml_file_types import ManifestFile


def get_release() -> str:
    """Get the komodo release from the active environment.

    The value of the KOMODO_RELEASE environment variable implicitly tells
    us the kind of environment we are in. If it looks like an ordinary name,
    it is probably a komodo environment. However, if it is a path, it is a
    komodoenv environment.

    We need to know the kind of environment because komodo and komodoenv
    environments store their manifest files (and root folders) in different
    places.
    """
    try:
        return os.environ["KOMODO_RELEASE"]
    except KeyError:
        message = textwrap.dedent(
            """
            No active komodo environment found.

            Either run this command from an active komodo or komodoenv
            environment, or provide an environment manifest file path with the
            --manifest-file option.\
            """,
        )
        sys.exit(message)


def read_config(fname: Union[str, Path]) -> dict:
    """Read an INI file (aka config file) that does not have sections.
    Sections are part of the INI file format specification and cannot be read
    by a `configparser.ConfigParser` without them. This function creates a
    temporary 'MAIN' section and passes back its contents.

    Args:
    ----
        fname: the path to a 'flat' config file, i.e. one with no sections.

    Returns:
    -------
        The configuration.
    """
    config = configparser.ConfigParser()
    with open(fname, encoding="utf-8") as stream:
        config.read_string("[MAIN]\n" + stream.read())
    return dict(config["MAIN"])


def get_komodoenv_path(release: str) -> Path:
    """Use the release name to find the 'real' release path, but from a
    komodoenv environment. These environments overwrite the environment
    variable $KOMODO_RELEASE and $PATH, but they store the original path
    in the komodoenv at 'root/pyvenv.cfg'.

    Args:
    ----
        release: The name of the release, e.g. as stored in the KOMODO_RELEASE
            environment variable.

    Returns:
    -------
        The path to the release, where the 'root/bin' folder is.
    """
    config = read_config(Path(release) / "komodoenv.conf")
    path = os.path.realpath(
        os.path.join(config["komodo-root"], config["current-release"])
    )
    if not os.path.isdir(os.path.join(path, "root")):
        path += "-" + config["linux-dist"]
    return Path(path)


def get_komodo_path(release: str) -> Path:
    """Use the release name to find the 'real' release path in an ordinary
    komodo environment. E.g., the release may be something like
    '2023.01.02-py38' but the 'real' release (where the release manifest
    is stored) might be platform-specific, e.g. '2023.01.02-py38-rhel7'.
    The real path is in the PATH, so we try to get it from there.

    Args:
    ----
        release: The name of the release, e.g. from $KOMODO_RELEASE.

    Returns:
    -------
        The path to the release, where the 'root/bin' folder is.
    """
    paths = os.environ["PATH"]
    pattern = re.compile(rf"(.*?{release}.*?)/root/bin")
    result = pattern.search(paths)
    if result is not None:
        (path,) = result.groups()
    else:
        message = f"Could not retrieve the path to the release {release}."
        raise RuntimeError(message)
    return Path(path)


def get_version(pkg: str, manifest: Optional[Dict] = None) -> str:
    """Get the release number (or git commit hash) for a package in a
    komodo release file. If no file is specified, the current release
    is used. If no environment is active, the path to the release
    must be specified.

    Args:
    ----
        pkg: The name of the package to get the version for.
        manifest: Optional. A mapping of packages to dicts of version and
            maintainer. Typically, this will come from the YAML file created
            by komodo when it builds a release.

    Returns:
    -------
        The version number or git hash of the version.
    """
    path = None
    if manifest is None:
        release = get_release()
        if (Path(release) / "komodoenv.conf").is_file():
            path = get_komodoenv_path(release)
        else:
            path = get_komodo_path(release)
        release_file = path.parts[-1]

        with open(path / release_file, encoding="utf-8") as stream:
            yaml = YAML()
            manifest = yaml.load(stream)

    package = manifest.get(pkg)

    if package is None:
        path_str = f" {path / release_file}" if path is not None else ""
        message = f"The package {pkg} is not found in the manifest file{path_str}."
        raise KeyError(message)

    return package.get("version")


def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse the arguments from the command line into an `argparse.Namespace`.
    Having a separated function makes it easier to test the CLI.

    Args:
    ----
        args: A sequence of arguments, e.g. as collected from the command line.

    Returns:
    -------
        The `argparse.Namespace`, a mapping of arg names to values.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Return the version of a specified package in the active "
            "release or in a given release manifest file."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("package", help="Package to find the version for.")
    parser.add_argument(
        "--manifest-file",
        type=ManifestFile(),
        required=False,
        help=(
            "The full path to a release manifest file. This file is "
            "produced by komodo when it builds an environment. If omitted, "
            "komodo-show-version will try to find the file for the active "
            "environment."
        ),
    )
    return parser.parse_args(args)


def main() -> int:
    """Run the CLI and return the result from get_version()."""
    args = parse_args(sys.argv[1:])
    print(get_version(args.package, manifest=args.manifest_file))
    return 0


if __name__ == "__main__":
    main()
