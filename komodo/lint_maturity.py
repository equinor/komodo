#!/usr/bin/env python

import argparse
import os
import sys
import warnings

import yaml
from packaging.version import InvalidVersion, Version, parse

_INVALID_TAGS = {
    "a": ["invalid"],
    "b": ["a", "invalid"],
    "rc": ["a", "b", "invalid"],
    "stable": ["a", "b", "rc", "invalid"],
    "exception": ["a", "b", "rc", "invalid"],
}


def print_system_exit_message(system_exit_msg):

    if system_exit_msg != "":
        raise SystemExit(system_exit_msg)


def print_warning_message(system_warning_msg):

    if system_warning_msg != "":
        warnings.warn(system_warning_msg, UserWarning)


def msg_packages_invalid(
    release_basename, release_version, count_tag_invalid, dict_tag_maturity
):

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


def msg_packages_exception(release_basename, dict_tag_maturity):

    msg_exception = ""

    if len(dict_tag_maturity["exception"]) > 0:
        msg_exception += release_basename + ", exception list of packages:\n"
        msg_exception += "\t" + str(dict_tag_maturity["exception"]) + " \n"

    return msg_exception


def count_invalid_tags(dict_tag_maturity, invalid_tags):

    count_tag_maturity = {tag: len(dict_tag_maturity[tag]) for tag in dict_tag_maturity}
    invalid_tags_count = sum(count_tag_maturity[tag] for tag in invalid_tags)

    return invalid_tags_count


def get_release_type(version_string):

    try:
        version = Version(version_string)
        release_type = "stable" if version.pre is None else version.pre[0]
    except InvalidVersion:
        release_type = "invalid"

    return release_type


def get_packages_info(packages_dict, tag_exceptions_package):

    dict_tag_maturity = {
        "a": [],
        "b": [],
        "rc": [],
        "stable": [],
        "exception": [],
        "invalid": [],
    }

    for package_name, package_version in packages_dict.items():

        if package_name not in tag_exceptions_package:
            release_version_package = get_release_type(package_version)
        else:
            release_version_package = "exception"
        dict_tag_maturity[release_version_package].append(
            (package_name, package_version)
        )

    return dict_tag_maturity


def read_yaml_file(file_path):

    with open(file_path) as yml_file:
        loaded_yaml_file = yaml.safe_load(yml_file)

    return loaded_yaml_file


def msg_release_exception(release_basename, release_version):

    msg_exception = ""

    if release_version == "exception":
        msg_exception += (
            release_basename + " not lint because it is in the exception list.\n"
        )

    return msg_exception


def get_release_version(release_basename, tag_exceptions_release):

    release_cleanname = release_basename.split("-")[0]

    if release_cleanname not in tag_exceptions_release:
        release_version = get_release_type(release_cleanname)
    else:
        release_version = "exception"

    return release_version


def run(files_to_lint, tag_exceptions):

    system_exit_msg = ""
    system_warning_msg = ""

    for file_to_lint in files_to_lint:

        release_basename = os.path.basename(file_to_lint)
        release_version = get_release_version(
            release_basename, tag_exceptions["release"]
        )
        system_warning_msg += msg_release_exception(release_basename, release_version)

        if release_version == "invalid":
            system_exit_msg += (
                release_basename + " is incompatible with version name.\n"
            )
        else:
            packages_dict = read_yaml_file(file_path=file_to_lint)
            dict_tag_maturity = get_packages_info(
                packages_dict, tag_exceptions["package"]
            )
            count_tag_invalid = count_invalid_tags(
                dict_tag_maturity, _INVALID_TAGS[release_version]
            )

            system_warning_msg += msg_packages_exception(
                release_basename, dict_tag_maturity
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

    print_warning_message(system_warning_msg)
    print_system_exit_message(system_exit_msg)


def get_files_to_lint(release_folder, release_file):

    if release_folder is None:
        files_to_lint = [release_file]
    else:
        files_to_lint = filter(
            lambda file: os.path.isfile(file),
            map(
                lambda file: os.path.join(release_folder, file),
                os.listdir(release_folder),
            ),
        )
    return files_to_lint


def define_tag_exceptions(tag_exception_arg):

    if os.path.isfile(tag_exception_arg[0]):
        tag_exceptions = read_yaml_file(file_path=tag_exception_arg[0])
    elif tag_exception_arg[0] == "":
        tag_exceptions = {"release": [], "package": []}
    else:
        exit_msg = str(tag_exception_arg) + " is not a valid file."
        raise SystemExit(exit_msg)

    return tag_exceptions


def get_parser():

    parser = argparse.ArgumentParser(description=("Lint the maturity of packages."))
    parser.add_argument(
        "--tag_exceptions",
        nargs="+",
        default=[""],
        help="One file with exceptions for (a) release tag and (b) packages tag.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--release_file",
        type=lambda arg: arg
        if os.path.isfile(arg)
        else parser.error("{} is not a valid file".format(arg)),
        help="Release file",
    )
    group.add_argument(
        "--release_folder",
        type=lambda arg: arg
        if os.path.isdir(arg)
        else parser.error("{} is not a valid directory".format(arg)),
        help="File with all package tags named as release version.",
    )

    return parser


def main():

    parser = get_parser()
    args = parser.parse_args()

    tag_exceptions = define_tag_exceptions(tag_exception_arg=args.tag_exceptions)

    files_to_lint = get_files_to_lint(
        release_folder=args.release_folder, release_file=args.release_file
    )

    run(files_to_lint, tag_exceptions)


if __name__ == "__main__":
    main()
