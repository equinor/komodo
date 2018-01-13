#!/usr/bin/env python
from __future__ import print_function

import unittest
import komodo

REPO = {
    'python': {
        'v2.7.14': {
            'maintainer': 'jokva@statoil.com',
            'make': 'sh',
            'makefile': 'configure',
            'source': 'git://github.com/python/cpython.git'
        }
    },
    'requests': {
        '2.18.4': {
            'depends': ['python'],
            'maintainer': 'jokva@statoil.com',
            'make': 'pip',
            'source': 'pypi'
        }
    },
}

RELEASE = {
    'python': 'v2.7.14',
    'requests': '2.18.4',
}

class TestLint(unittest.TestCase):

    def test_lint(self):
        lint_report = komodo.lint(RELEASE, REPO)
        self.assertEqual([], lint_report.dependencies)
        self.assertEqual([], lint_report.versions)

if __name__ == '__main__':
    unittest.main()
