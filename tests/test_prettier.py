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
        ugly_repository = TestPrettier.get_yaml_string('ugly_repository.yml')
        pretty_repository = TestPrettier.get_yaml_string('pretty_repository.yml')
        self.assertEqual(komodo.prettier(ugly_repository), pretty_repository)

    def test_release_prettifying(self):
        ugly_release = TestPrettier.get_yaml_string('ugly_release.yml')
        pretty_release = TestPrettier.get_yaml_string('pretty_release.yml')
        self.assertEqual(komodo.prettier(ugly_release), pretty_release)

    def test_duplicate_entries(self):
        duplicate_repository = TestPrettier.get_yaml_string('duplicate_repository.yml')
        with self.assertRaises(SystemExit):
            komodo.prettier(duplicate_repository)

    def test_inconsistent_config(self):
        inconsistent_config = TestPrettier.get_yaml_string('inconsistent_config.yml')
        with self.assertRaises(ValueError):
            komodo.prettier(inconsistent_config)


if __name__ == '__main__':
    unittest.main()
