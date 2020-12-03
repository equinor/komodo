import argparse

import yaml as yml


class YamlFile(argparse.FileType):
    def __init__(self, *args, **kwargs):
        super().__init__("r", *args, **kwargs)

    def __call__(self, value):
        file_handle = super().__call__(value)
        yaml = yml.safe_load(file_handle)
        file_handle.close()
        return yaml
