from pathlib import Path

import pytest

from komodo.prettier import load_yaml, prettier

INPUT_FOLDER = Path(__file__).resolve().parent / "input"


def get_yaml_string(filename):
    return (INPUT_FOLDER / filename).read_text(encoding="utf-8")


def test_repository_prettifying():
    assert prettier(load_yaml(INPUT_FOLDER / "ugly_repository.yml")) == get_yaml_string(
        "pretty_repository.yml",
    )


def test_release_prettifying():
    assert prettier(load_yaml(INPUT_FOLDER / "ugly_release.yml")) == get_yaml_string(
        "pretty_release.yml",
    )


def test_duplicate_entries():
    with pytest.raises(SystemExit):
        load_yaml(INPUT_FOLDER / "duplicate_repository.yml")
