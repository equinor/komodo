import argparse
import os
from pathlib import Path
from typing import Any, Dict

import yaml as yml


class YamlFile(argparse.FileType):
    def __init__(self, *args, **kwargs):
        super().__init__("r", *args, **kwargs)

    def __call__(self, value):
        file_handle = super().__call__(value)
        yaml = yml.safe_load(file_handle)
        file_handle.close()
        return yaml


class ReleaseFile(YamlFile):
    def __call__(self, value: str) -> Dict[str, Dict[Any, Any]]:
        yaml = super().__call__(value)
        return {Path(value).stem: yaml}


class ReleaseDir:
    def __call__(self, value: str) -> Dict[str, YamlFile]:
        if not os.path.isdir(value):
            raise NotADirectoryError(value)
        result = {}
        for yml_file in Path(value).glob("*.yml"):
            result.update(ReleaseFile()(yml_file))
        return result


class ManifestFile(YamlFile):
    """
    Return the data from 'manifest' YAML, but validate it first.
    """

    def __call__(self, value: str) -> Dict[str, Dict[str, str]]:
        yaml = super().__call__(value)
        message = (
            "The file you provided does not appear to be a manifest file "
            "produced by komodo. It may be a release file. Manifest files "
            "have a format like the following:\n\n"
            "python:\n  maintainer: foo@example.com\n  version: 3-builtin\n"
            "treelib:\n  maintainer: foo@example.com\n  version: 1.6.1\n"
        )
        for _, metadata in yaml.items():
            assert isinstance(metadata, dict), message
            assert isinstance(metadata["version"], str), message
        return yaml
