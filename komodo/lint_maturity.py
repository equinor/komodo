#!/usr/bin/env python

import argparse
import os
import sys
import warnings
from typing import Any, Iterable, List, Mapping, MutableSequence, Sequence, Tuple

import yaml
from packaging.version import InvalidVersion, Version

from komodo.yaml_file_types import ReleaseFile

_INVALID_TAGS = {
    "a": ["invalid"],
    "b": ["a", "invalid"],
    "rc": ["a", "b", "invalid"],
    "stable": ["a", "b", "rc", "invalid"],
    "exception": ["a", "b", "rc", "invalid"],
}


_Maturities = Mapping[str, Sequence[Tuple[str, str]]]
_Tags = Mapping[str, Sequence[str]]


def msg_packages_invalid(
    release_basename: str,
    release_version: str,
    count_tag_invalid: int,
    dict_tag_maturity: _Maturities,
) -> str:
    exit_msg = ""
    exit_msg += (
        release_basename
        + " has "
        + str(count_tag_invalid)
        + " packages with invalid maturity tag.\n"
    )

    for tag in _INVALID_TAGS[release_version]:
        if len(dict_tag_maturity[tag]) > 0:
            exit_msg += (
                "\tTag " + tag + " packages: " + str(dict_tag_maturity[tag]) + "\n"
            )

    return exit_msg


def msg_packages_exception(
    release_basename: str, dict_tag_maturity: _Maturities
) -> str:
    msg_exception = ""

    if len(dict_tag_maturity["exception"]) > 0:
        msg_exception += release_basename + ", exception list of packages:\n"
        msg_exception += "\t" + str(dict_tag_maturity["exception"]) + "\n"

    return msg_exception


def count_invalid_tags(
    dict_tag_maturity: Mapping[str, Sequence[Tuple[str, str]]],
    invalid_tags: Sequence[str],
) -> int:
    count_tag_maturity = {tag: len(dict_tag_maturity[tag]) for tag in dict_tag_maturity}
    return sum(count_tag_maturity[tag] for tag in invalid_tags)


def get_release_type(version: str) -> str:
    try:
        parsed = Version(version)
        release_type = "stable" if parsed.pre is None else parsed.pre[0]
    except InvalidVersion:
        release_type = "invalid"

    return release_type


def get_packages_info(
    release_file: ReleaseFile, tag_exceptions_package: Sequence[str]
) -> Mapping[str, Sequence[Tuple[str, str]]]:
    dict_tag_maturity: Mapping[str, MutableSequence[Tuple[str, str]]] = {
        "a": [],
        "b": [],
        "rc": [],
        "stable": [],
        "exception": [],
        "invalid": [],
    }

    for package_name, package_version in release_file.content.items():
        if package_name not in tag_exceptions_package:
            release_version_package = get_release_type(package_version)
        else:
            release_version_package = "exception"
        dict_tag_maturity[release_version_package].append(
            (package_name, package_version),
        )

    return dict_tag_maturity


def msg_release_exception(release_basename: str, release_version: str) -> str:
    msg_exception = ""

    if release_version == "exception":
        msg_exception += (
            release_basename + " not lint because it is in the exception list.\n"
        )

    return msg_exception


def get_release_version(
    release_basename: str, tag_exceptions_release: Sequence[str]
) -> str:
    if release_basename not in tag_exceptions_release:
        release_version = get_release_type(release_basename)
    else:
        release_version = "exception"

    return release_version


def run(
    files_to_lint: Iterable[str], tag_exceptions: Mapping[str, Sequence[str]]
) -> None:
    system_exit_msg = ""
    system_warning_msg = ""

    for file_to_lint in files_to_lint:
        release_basename = ".".join(os.path.basename(file_to_lint).split(".")[0:-1])
        release_version = get_release_version(
            release_basename,
            tag_exceptions["release"],
        )
        system_warning_msg += msg_release_exception(release_basename, release_version)

        if release_version == "invalid":
            system_exit_msg += (
                release_basename + " is incompatible with version name.\n"
            )
        else:
            with open(file_to_lint, encoding="utf-8") as f:
                release_file = ReleaseFile().from_yaml_string(f.read())

            dict_tag_maturity = get_packages_info(
                release_file,
                tag_exceptions["package"],
            )
            count_tag_invalid = count_invalid_tags(
                dict_tag_maturity,
                _INVALID_TAGS[release_version],
            )

            system_warning_msg += msg_packages_exception(
                release_basename,
                dict_tag_maturity,
            )

            if count_tag_invalid > 0:
                packages_msg = msg_packages_invalid(
                    release_basename,
                    release_version,
                    count_tag_invalid,
                    dict_tag_maturity,
                )

                if release_version != "exception":
                    system_exit_msg += packages_msg
                else:
                    system_warning_msg += packages_msg

    if system_warning_msg:
        warnings.warn(system_warning_msg, UserWarning, stacklevel=2)
    if system_exit_msg:
        sys.exit(system_exit_msg)


def read_yaml_file_and_convert_to_release_file(release_file_path: str) -> ReleaseFile:
    with open(release_file_path, mode="r+", encoding="utf-8") as f:
        release_file_yaml_string = f.read()
    return ReleaseFile().from_yaml_string(value=release_file_yaml_string)


def get_files_to_lint(release_folder: str, release_file: str) -> Iterable[str]:
    if release_folder is None:
        files_to_lint = [release_file]
    else:
        files_to_lint = filter(
            lambda file: os.path.isfile,
            (
                os.path.join(release_folder, file_path)
                for file_path in os.listdir(release_folder)
            ),
        )
    return files_to_lint


def define_tag_exceptions(tag_exception_arg: Sequence[str]) -> _Tags:
    if os.path.isfile(tag_exception_arg[0]):
        with open(tag_exception_arg[0]) as f:
            tag_exceptions = yaml.safe_load(f)
    elif tag_exception_arg[0] == "":
        tag_exceptions = {"release": [], "package": []}
    else:
        exit_msg = str(tag_exception_arg) + " is not a valid file."
        raise SystemExit(exit_msg)

    return tag_exceptions


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lint the maturity of packages.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--tag_exceptions",
        nargs="+",
        default=[""],
        help="One file with exceptions for (a) release tag and (b) packages tag.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--release_file",
        type=lambda arg: (
            arg if os.path.isfile(arg) else parser.error(f"{arg} is not a valid file")
        ),
        help="Komodo release file in YAML format.",
    )
    group.add_argument(
        "--release_folder",
        type=lambda arg: (
            arg
            if os.path.isdir(arg)
            else parser.error(f"{arg} is not a valid directory")
        ),
        help="File with all package tags named as release version.",
    )

    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    tag_exceptions = define_tag_exceptions(tag_exception_arg=args.tag_exceptions)

    files_to_lint = get_files_to_lint(
        release_folder=args.release_folder,
        release_file=args.release_file,
    )

    run(files_to_lint, tag_exceptions)


if __name__ == "__main__":
    main()
