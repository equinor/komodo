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
