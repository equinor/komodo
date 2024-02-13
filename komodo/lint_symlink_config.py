import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Union

from komodo.symlink.sanity_check import assert_root_nodes


def parse_args():
    parser = argparse.ArgumentParser(
        description=("Verify symlink configuration file for komodo is valid."),
    )
    parser.add_argument(
        "config",
        type=Path,
        help="a json file describing symlink structure",
    )
    return parser.parse_args()


def lint_symlink_config(link_dict: Mapping[str, Union[Mapping, str]]):
    assert_root_nodes(link_dict)
    print("Symlink configuration file is valid!")


def main():
    args = parse_args()
    if not os.path.isfile(args.config):
        sys.exit(f"The file {args.config} cannot be found")
    with open(args.config, mode="r", encoding="utf-8") as config_file_handler:
        symlink_config = json.load(config_file_handler)
    lint_symlink_config(symlink_config)


if __name__ == "__main__":
    main()
