import argparse
import json
import os
import re
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

    links = link_dict["links"]
    komodo_release_regex = r"^\d{4}\.\d{2}\..*-py\d+$"

    for dest in links.values():
        if (
            dest not in links
            and "bleeding-py" not in dest
            and not re.search(komodo_release_regex, dest)
        ):
            raise SystemExit(f"Missing symlink {dest}")

    print("Symlink configuration file is valid!")


def main():
    args = parse_args()
    if not os.path.isfile(args.config):
        sys.exit(f"The file {args.config} cannot be found")
    with open(args.config, encoding="utf-8") as config_file_handler:
        symlink_config = json.load(config_file_handler)
    lint_symlink_config(symlink_config)


if __name__ == "__main__":
    main()
