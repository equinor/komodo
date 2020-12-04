import os
import sys
from argparse import ArgumentError, ArgumentParser, ArgumentTypeError

from komodo.prettier import load_yaml, prettier, prettified_yaml, write_to_file


def load_all_releases(files):

    used_versions = {}

    for filename in files:
        current_release = load_yaml(filename)

        for lib, version in current_release.items():
            if lib in used_versions:
                used_versions[lib].append(version)
            else:
                used_versions[lib] = [version]

    return used_versions


def find_unused_versions(used_versions, repository):
    unused_versions = {}
    for lib, versions in repository.items():
        for version in versions:
            if lib in used_versions and version in used_versions[lib]:
                continue

            if lib in unused_versions:
                unused_versions[lib].append(version)
            else:
                unused_versions[lib] = [version]

    return unused_versions


def remove_unused_versions(repository, unused_versions):
    for lib, versions in unused_versions.items():
        for version in versions:
            repository[lib].pop(version)
        if len(repository[lib]) == 0:
            repository.pop(lib)


def _is_yml(path):
    _, ext = os.path.splitext(path)
    return ext == ".yml"


def _get_yml_files(path_name):
    current_path = os.path.realpath(path_name)
    files = os.listdir(path_name)
    yml_files = []
    for filename in files:
        file_path = os.path.join(current_path, filename)

        if not _is_yml(file_path):
            continue
        yml_files.append(file_path)
    return yml_files


def _valid_path_or_files(path):

    yml_files = []

    full_path = os.path.realpath(path)
    if os.path.isdir(full_path):
        yml_files += _get_yml_files(full_path)
    elif os.path.isfile(full_path) and _is_yml(full_path):
        yml_files.append(full_path)
    else:
        raise ArgumentTypeError("{} is not a valid yml-file or folder".format(path))
    return yml_files


def add_cleanup_parser(subparsers):
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        description="Clean up unused versions the repository file based on a set of releases",
    )
    cleanup_parser.set_defaults(func=run_cleanup)
    cleanup_parser.add_argument(
        "--check",
        action="store_true",
        help="Only print out unused library versions",
        required=False,
    )
    cleanup_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Output resulting repository-file to stdout",
        required=False,
    )
    cleanup_parser.add_argument(
        "--repository",
        type=str,
        help="a yml file defining all libraries and their versions",
    )
    cleanup_parser.add_argument(
        "--releases",
        type=_valid_path_or_files,
        help="list of release files or folders containing releases",
        nargs="+",
    )
    cleanup_parser.add_argument(
        "--output", type=str, help="name of file to write new repository"
    )


def add_prettier_parser(subparsers):

    prettier_parser = subparsers.add_parser(
        "prettier",
        description=(
            "Check and/or format the Komodo configuration files. "
            "Takes in any number of yml files, which could be e.g. the main "
            "Komodo repository and an arbitrary number of releases. "
            "Throws a hard error if the same package is defined multiple times."
        ),
    )
    prettier_parser.set_defaults(func=run_prettier)
    prettier_parser.add_argument(
        "--files",
        type=_valid_path_or_files,
        help="list of yaml files or folders containing yaml",
        nargs="+",
    )
    prettier_parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not write the files back, just return the status. "
            "Return code 0 means nothing would change. "
            "Return code 1 means some files would be reformatted."
        ),
        required=False,
    )


def run_cleanup(args, parser):
    if args.check and args.stdout:
        parser.error(
            ArgumentError(
                message="Only check, stdout can not be used together!",
                argument=args.check,
            )
        )
    repository = load_yaml(args.repository)
    release_files = [filename for sublist in args.releases for filename in sublist]
    used_versions = load_all_releases(release_files)
    unused_versions = find_unused_versions(used_versions, repository)

    if args.check:
        if not unused_versions:
            print("No unused software versions found!")
        else:
            print("The following software version are not in use:")
        for lib, versions in unused_versions.items():
            print(lib, versions)
        return

    remove_unused_versions(repository=repository, unused_versions=unused_versions)

    if args.stdout:
        print(prettier(repository))
        return

    output_file = args.repository
    if args.output:
        output_file = args.output
    write_to_file(repository, output_file)
    if unused_versions:
        print("Success! New repository file written to {}".format(output_file))
        print("The following software version are not in use:")
        for lib, versions in unused_versions.items():
            print(lib, versions)


def run_prettier(args, _):
    release_files = [filename for sublist in args.files for filename in sublist]

    sys.exit(0) if all(
        [prettified_yaml(filename, args.check) for filename in release_files]
    ) or not args.check else sys.exit(1)


def main(args=None):
    parser = ArgumentParser(description="Tidy up release and repository files.")

    subparsers = parser.add_subparsers(
        title="Available user entries",
        description="time to tidy up",
        help="Available sub commands",
        dest="mode",
    )
    add_cleanup_parser(subparsers)
    add_prettier_parser(subparsers)
    args = parser.parse_args(args)

    args.func(args, parser)


if __name__ == "__main__":
    main()
