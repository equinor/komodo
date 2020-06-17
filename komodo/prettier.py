from __future__ import print_function

import os
import re
import sys
import argparse
import functools

# On Python3, StringIO can come from standard library io:
from ruamel.yaml.compat import StringIO
import ruamel.yaml


def repository_specific_formatting(empty_line_top_level, yaml_string):
    """Transform function to ruamel.yaml's dump function. Makes sure there are
    only empty lines inbetween different top level keys (if empty_line_top_level
    is True, otherwise no empty lines).
    """

    yaml_string = re.sub(r"\n+", r"\n", yaml_string)  # Remove all empty lines

    if empty_line_top_level:
        yaml_string = re.sub(  # Add one empty line between each package
            r"(\n[^\#][^\n]*)\n([^\s])", r"\1\n\n\2", yaml_string
        )

    return yaml_string


def is_repository(config):
    """Returns `False` if the configuration corresponds to a Komodo release
    (all config elements below top level key are strings). Returns `True` if
    it corresponds to a _repository_ (all config elements below top level key are
    themselves dictionaries).

    Raises ValueError if inconsistent throughout the config.
    """

    # For Python2+3 compatibility. On Python3-only, use isinstance(x, str)
    # instead of isinstance(x, basestring).
    try:
        basestring
    except NameError:
        basestring = str  # No basestring on Python3

    if all([isinstance(package, basestring) for package in config.values()]):
        return False
    elif all(
        [
            isinstance(package, ruamel.yaml.comments.CommentedMap)
            for package in config.values()
        ]
    ):
        return True

    raise ValueError(
        "Inconsistent configuration file. "
        "Not able to detect if it is a release or repository."
    )


def prettier(yaml_input_dict):
    """Takes in a string corresponding to a YAML Komodo configuration, and returns
    the corresponding prettified YAML string."""

    ruamel_instance = ruamel.yaml.YAML()
    ruamel_instance.indent(  # Komodo prefers two space indendation
        mapping=2, sequence=4, offset=2
    )
    ruamel_instance.width = 1000  # Avoid ruamel wrapping long

    komodo_repository = is_repository(yaml_input_dict)

    # On Python3.6+, sorted_config can just be an
    # ordinary dict as insertion order is then preserved.
    sorted_config = ruamel.yaml.comments.CommentedMap()
    for package in sorted(yaml_input_dict, key=str.lower):
        sorted_config[package] = yaml_input_dict[package]

    setattr(sorted_config, ruamel.yaml.comments.comment_attrib, yaml_input_dict.ca)

    yaml_output = StringIO()
    ruamel_instance.dump(
        sorted_config,
        yaml_output,
        transform=functools.partial(repository_specific_formatting, komodo_repository),
    )

    if sys.version_info < (3, 0):
        # Need to encode the byte-string on Python2
        return yaml_output.getvalue().encode("utf-8")

    return yaml_output.getvalue()


def prettified_yaml(filepath, check_only=True):
    """Returns `True` if the file is already "prettified", `False` otherwise.
    If `check_only` is False, the input file will be "prettified" in place if necessary.
    """

    print("Checking {}... ".format(filepath), end="")
    with open(file=filepath, mode="r") as input_file:
        yaml_original = input_file.read()

    yaml_input = load_yaml(filepath)

    yaml_prettified_string = prettier(yaml_input)

    if yaml_prettified_string != yaml_original:
        print("{} reformatted!".format("would be" if check_only else ""))
        if not check_only:
            with open(filepath, "w") as fh:
                fh.write(yaml_prettified_string)
        return False

    print("looking good!")
    return True


def write_to_file(repository, filename):
    if type(repository) == dict:
        repository = ruamel.yaml.comments.CommentedMap(repository)
    output_str = prettier(repository)
    with open(file=filename, mode="w") as output_file:
        output_file.write(output_str)


def load_yaml(filename):
    if not os.path.isfile(os.path.realpath(filename)):
        raise argparse.ArgumentTypeError("{} is not a valid file".format(filename))

    ruamel_instance = ruamel.yaml.YAML()
    ruamel_instance.indent(  # Komodo prefers two space indendation
        mapping=2, sequence=4, offset=2
    )
    ruamel_instance.width = 1000  # Avoid ruamel wrapping long

    try:
        with open(filename) as repo_handle:
            input_dict = ruamel_instance.load(repo_handle)
        return input_dict

    except (
        ruamel.yaml.scanner.ScannerError,
        ruamel.yaml.constructor.DuplicateKeyError,
    ) as e:
        raise SystemExit(
            "The file: <{}> contains invalid YAML syntax:\n {}".format(filename, str(e))
        )
