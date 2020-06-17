#!/usr/bin/env python

import os
import unittest

from ruamel.yaml.constructor import DuplicateKeyError

import komodo


INPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "input")


class TestPrettier(unittest.TestCase):
    @staticmethod
    def get_yaml_string(filename):
        with open(os.path.join(INPUT_FOLDER, filename)) as fh:
            return fh.read()

    def test_repository_prettifying(self):
        pretty_repository = TestPrettier.get_yaml_string("pretty_repository.yml")
        self.assertEqual(
            komodo.prettier(
                komodo.load_yaml(os.path.join(INPUT_FOLDER, "ugly_repository.yml"))
            ),
            pretty_repository,
        )

    def test_release_prettifying(self):
        pretty_release = TestPrettier.get_yaml_string("pretty_release.yml")
        self.assertEqual(
            komodo.prettier(
                komodo.load_yaml(os.path.join(INPUT_FOLDER, "ugly_release.yml"))
            ),
            pretty_release,
        )

    def test_duplicate_entries(self):
        with self.assertRaises(SystemExit):
            komodo.load_yaml(os.path.join(INPUT_FOLDER, "duplicate_repository.yml"))

    def test_inconsistent_config(self):
        with self.assertRaises(ValueError):
            komodo.prettier(
                komodo.load_yaml(os.path.join(INPUT_FOLDER, "inconsistent_config.yml"))
            )


if __name__ == "__main__":
    unittest.main()
