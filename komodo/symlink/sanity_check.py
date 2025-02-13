import argparse
import difflib
import json
import os
import pprint
import re
import sys


def equal_links(dict_a, dict_b):
    if dict_a["root_folder"] != dict_b["root_folder"]:
        return False

    if set(dict_a["root_links"]) != set(dict_b["root_links"]):
        return False

    return dict_a["links"] == dict_b["links"]


def _linked_to(s_link, list_of_files):
    for file_name in list_of_files:
        if os.path.islink(file_name) and os.readlink(file_name) == s_link:
            return True

    return False


def read_link_structure(path):
    link_structure = {
        "root_folder": os.path.realpath(path),
        "root_links": [],
        "links": {},
    }

    list_of_files = [os.path.join(path, file_name) for file_name in os.listdir(path)]

    bleeding_timestamp_pattern = r"bleeding-\d{8}-\d{4}-"
    bleeding_deleteme_pattern = r"bleeding-.*\.deleteme"
    bleeding_py_version_pattern = r"bleeding-py\d{2}"
    dangling_root_folders = [
        "bleeding-py311-rhel8",
        "bleeding-py38-rhel7",
        "bleeding-py38-rhel8",
    ]

    for file_path in list_of_files:
        file_name = os.path.basename(file_path)

        if not any(
            [
                re.match(bleeding_timestamp_pattern, file_name),
                re.match(bleeding_deleteme_pattern, file_name),
                re.match(bleeding_py_version_pattern, file_name),
                file_name in dangling_root_folders,
                not os.path.islink(file_path),
            ]
        ):
            link_structure["links"][file_name] = os.path.basename(
                os.readlink(file_path),
            )
            if not _linked_to(file_name, list_of_files):
                link_structure["root_links"].append(file_name)

    return link_structure


def _check_link(link, link_dict, errors, visited):
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


def verify_integrity(link_dict):
    errors = []

    for link in link_dict["links"].values():
        _check_link(link, link_dict, errors, [])

    return errors


def _get_root_nodes(link_dict):
    keys = set(link_dict["links"].keys())
    values = set(link_dict["links"].values())
    return keys.difference(values)


def suggest_missing_roots(link_dict):
    input_roots = link_dict.get("root_links", [])
    inferred_roots = _get_root_nodes(link_dict)
    if set(input_roots) != inferred_roots:
        return sorted(set(inferred_roots).difference(input_roots))
    return []


def assert_root_nodes(link_dict):
    input_roots = link_dict["root_links"]
    inferred_roots = _get_root_nodes(link_dict)
    if set(input_roots) != inferred_roots:
        raise AssertionError(
            "The roots in the link-tree do not match "
            + "the roots defined in the root_links dict\n"
            + f"Roots defined: {set(input_roots)}\n"
            + f"Roots expected: {inferred_roots}\n"
            + f"Missing root(s): {str(list(set(inferred_roots).difference(input_roots)))}\n"
            + f"Incorrectly added root(s): {str(list(set(input_roots).difference(inferred_roots)))}"
        )


def _sort_lists_in_dicts(_dict: dict) -> dict:
    result = {}
    for key, value in _dict.items():
        if isinstance(value, list):
            result[key] = sorted(value)
        else:
            result[key] = value
    return result


def _compare_dicts(dict_1: dict, dict_2: dict) -> str:
    return "\n" + "\n".join(
        difflib.ndiff(
            pprint.pformat(_sort_lists_in_dicts(dict_1)).splitlines(),
            pprint.pformat(_sort_lists_in_dicts(dict_2)).splitlines(),
        ),
    )


def sanity_main():
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
