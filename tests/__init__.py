import os
import ruamel.yaml

def _get_test_root():
    return os.path.realpath(os.path.dirname(__file__))

def _load_yaml(filename):
    ruamel_instance = ruamel.yaml.YAML()
    ruamel_instance.indent(  # Komodo prefers two space indendation
        mapping=2, sequence=4, offset=2
    )
    ruamel_instance.width = 1000  # Avoid ruamel wrapping long
    with open(filename) as repo_handle:
        input_dict = ruamel_instance.load(repo_handle)
    return input_dict