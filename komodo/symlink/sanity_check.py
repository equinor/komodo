import argparse
import difflib
import json
import os
import pprint
import sys
from typing import (
    AbstractSet,
    Any,
    MutableSequence,
    Sequence,
)

from komodo.symlink.types import LinkDict


def equal_links(a: LinkDict, b: LinkDict) -> bool:
    if a["root_folder"] != b["root_folder"]:
        return False

    if set(a["root_links"]) != set(b["root_links"]):
        return False

    return a["links"] == b["links"]


def _linked_to(s_link: str, list_of_files: Sequence[str]) -> bool:
    for file_name in list_of_files:
        if os.path.islink(file_name) and os.readlink(file_name) == s_link:
            return True

    return False


def read_link_structure(path: str) -> LinkDict:
    link_structure: Any = {
        "root_folder": os.path.realpath(path),
        "root_links": [],
        "links": {},
    }

    list_of_files = [os.path.join(path, file_name) for file_name in os.listdir(path)]
    for file_path in list_of_files:
        file_name = os.path.basename(file_path)
        if os.path.islink(file_path):
            link_structure["links"][file_name] = os.path.basename(
                os.readlink(file_path),
            )
            if not _linked_to(file_name, list_of_files):
                link_structure["root_links"].append(file_name)

    return link_structure


def _check_link(
    link: str,
    link_dict: LinkDict,
    errors: MutableSequence[str],
    visited: MutableSequence[str],
) -> None:
    if link in visited:
        error = f"{link} is part of a cyclic symlink"
        if error not in errors:
            errors.append(error)
        return

    visited.append(link)

    if link in link_dict["links"]:
        _check_link(link_dict["links"][link], link_dict, errors, visited)

    elif not os.path.exists(os.path.join(link_dict["root_folder"], link)):
        error = f"{link} does not exist"
        if error not in errors:
            errors.append(error)


def verify_integrity(link_dict: LinkDict) -> Sequence[str]:
    errors: MutableSequence[str] = []

    for link in link_dict["links"].values():
        _check_link(link, link_dict, errors, [])

    return errors


def _get_root_nodes(link_dict: LinkDict) -> AbstractSet[str]:
    keys = set(link_dict["links"].keys())
    values = set(link_dict["links"].values())
    return keys.difference(values)


def assert_root_nodes(link_dict: LinkDict) -> None:
    input_roots = link_dict["root_links"]
    inferred_roots = _get_root_nodes(link_dict)
    if set(input_roots) != inferred_roots:
        raise AssertionError(
            "The roots in the link-tree is not matching "
            + "the roots defined in link_roots in dict\n"
            + f"Roots defined: {set(input_roots)}\n"
            + f"Roots expected: {inferred_roots}",
        )


def _compare_dicts(d1: Any, d2: Any) -> str:
    return "\n" + "\n".join(
        difflib.ndiff(pprint.pformat(d1).splitlines(), pprint.pformat(d2).splitlines()),
    )


def sanity_main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify symlinks for komodo versions are according to a given config."
        ),
    )
    parser.add_argument(
        "config",
        type=str,
        help="a json file describing symlink structure",
    )

    args = parser.parse_args()
    if not os.path.isfile(args.config):
        sys.exit(f"The file {args.config} cannot be found")

    with open(args.config, encoding="utf-8") as file:
        input_dict = json.load(file)
    assert_root_nodes(input_dict)
    from_dir = read_link_structure(input_dict["root_folder"])

    if not equal_links(input_dict, from_dir):
        print(
            f"The config file: {args.config} does not match with the "
            "current folder structure",
        )
        print(_compare_dicts(input_dict, from_dir))
        sys.exit(1)

    print("Success: The folder structure matches the given config file!")
