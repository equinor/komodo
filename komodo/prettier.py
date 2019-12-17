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
    '''Transform function to ruamel.yaml's dump function. Makes sure there are
    only empty lines inbetween different top level keys (if empty_line_top_level
    is True, otherwise no empty lines).
    '''

    yaml_string = re.sub(r'\n+', r'\n', yaml_string)  # Remove all empty lines

    if empty_line_top_level:
        yaml_string = re.sub(  # Add one empty line between each package
            r'(\n[^\#][^\n]*)\n([^\s])', r'\1\n\n\2', yaml_string
        )

    return yaml_string


def is_repository(config):
    '''Returns `False` if the configuration corresponds to a Komodo release
    (all config elements below top level key are strings). Returns `True` if
    it corresponds to a _repository_ (all config elements below top level key are
    themselves dictionaries).

    Raises ValueError if inconsistent throughout the config.
    '''

    # For Python2+3 compatibility. On Python3-only, use isinstance(x, str)
    # instead of isinstance(x, basestring).
    try:
        basestring
    except NameError:
        basestring = str # No basestring on Python3

    if all([isinstance(package, basestring) for package in config.values()]):
        return False
    elif all([isinstance(package, ruamel.yaml.comments.CommentedMap)
              for package in config.values()]):
        return True

    raise ValueError(
        'Inconsistent configuration file. '
        'Not able to detect if it is a release or repository.'
    )


def prettier(yaml_input_string):
    '''Takes in a string corresponding to a YAML Komodo configuration, and returns
    the corresponding prettified YAML string.'''

    ruamel_instance = ruamel.yaml.YAML()
    ruamel_instance.indent(  # Komodo prefers two space indendation
        mapping=2, sequence=4, offset=2
    )
    ruamel_instance.width = 1000  # Avoid ruamel wrapping long

    try:
        config = ruamel_instance.load(yaml_input_string)
    except ruamel.yaml.constructor.DuplicateKeyError as e:
        raise SystemExit(str(e))

    komodo_repository = is_repository(config)

    # On Python3.6+, sorted_config can just be an
    # ordinary dict as insertion order is then preserved.
    sorted_config = ruamel.yaml.comments.CommentedMap()
    for package in sorted(config, key=str.lower):
        sorted_config[package] = config[package]

    setattr(sorted_config, ruamel.yaml.comments.comment_attrib, config.ca)

    yaml_output = StringIO()
    ruamel_instance.dump(
        sorted_config,
        yaml_output,
        transform=functools.partial(repository_specific_formatting, komodo_repository)
    )

    if sys.version_info < (3, 0):
        # Need to encode the byte-string on Python2
        return yaml_output.getvalue().encode('utf-8')

    return yaml_output.getvalue()


def prettified_yaml(filepath, check_only=True):
    '''Returns `True` if the file is already "prettified", `False` otherwise.
    If `check_only` is False, the input file will be "prettified" in place if necessary.
    '''

    print('Checking {}... '.format(filepath), end='')

    with open(filepath, 'r') as fh:
        yaml_input_string = fh.read()

    yaml_prettified_string = prettier(yaml_input_string)

    if yaml_prettified_string != yaml_input_string:
        print('{} reformatted!'.format('would be' if check_only else ''))
        if not check_only:
            with open(filepath, 'w') as fh:
                fh.write(yaml_prettified_string)
        return False

    print('looking good!')
    return True


def prettier_main():
    '''Main function doing user argument parsing and calling necessary functions.
    '''

    parser = argparse.ArgumentParser(
        description=(
            'Check and/or format the Komodo configuration files. '
            'Takes in any number of yml files, which could be e.g. the main '
            'Komodo repository and an arbitrary number of releases. '
            'Throws a hard error if the same package is defined multiple times.'
        )
    )
    parser.add_argument(
        'files',
        type=lambda arg: arg if os.path.isfile(arg) \
            else parser.error('{} is not a file'.format(arg)),
        nargs='+',
        help='One or more files to format/check',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help=(
            'Do not write the files back, just return the status. '
            'Return code 0 means nothing would change. '
            'Return code 1 means some files would be reformatted.'
        ),
    )

    args = parser.parse_args()

    sys.exit(0) if all(
        [prettified_yaml(filename, args.check) for filename in args.files]
    ) or not args.check else sys.exit(1)


if __name__ == '__main__':
    prettier_main()
