import argparse
import json
import os
import sys
from contextlib import contextmanager

from .sanity_check import verify_integrity


@contextmanager
def working_dir(path):
    prev_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_dir)


def _create_link(src, dst, link_dict):
    if src in link_dict and not os.path.exists(src):
        _create_link(link_dict[src], src, link_dict)

    if not os.path.exists(src):
        msg = f"{src} does not exist"
        raise ValueError(msg)

    if os.path.exists(dst) and os.path.islink(dst):
        existing_link = os.readlink(dst)
        if existing_link == src:
            return
        os.remove(dst)
        print(f"Existing symlink {dst} moved from {existing_link} to {src}")
    else:
        print(f"Created new symlink {dst} pointing to {src}")

    os.symlink(src, dst)


def create_symlinks(links_dict):
    root_folder = links_dict["root_folder"]
    if not os.path.isabs(root_folder):
        msg = "The root folder specified is not absolute"
        raise ValueError(msg)

    if not os.path.isdir(root_folder):
        msg = f"{root_folder} is not a directory or does not exist"
        raise ValueError(msg)

    with working_dir(root_folder):
        for dst, src in links_dict["links"].items():
            _create_link(src, dst, links_dict["links"])


def symlink_main():
    parser = argparse.ArgumentParser(description="Create symlinks for komodo versions.")
    parser.add_argument(
        "config",
        type=str,
        help="a json file describing symlink structure",
    )

    args = parser.parse_args()
    if not os.path.isfile(args.config):
        sys.exit(f"The file {args.config} can not be found")

    with open(args.config) as input_file:
        input_dict = json.load(input_file)

    errors = verify_integrity(input_dict)
    if errors:
        print("The following errors where found in the config file:")
        for e in errors:
            print(e)
        sys.exit(1)

    create_symlinks(input_dict)
