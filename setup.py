#!/usr/bin/env python
from __future__ import print_function

from setuptools import setup

setup(
    name='Komodo',
    version='1.0',
    packages=['komodo'],
    package_dir={'komodo' : 'komodo'},
    scripts=['bin/kmd'],
    test_suite='tests',
    install_requires=['shell', 'PyYAML'],
    entry_points={
        'console_scripts': [
            'komodo-lint = komodo.lint:lint_main',
            'komodo-prettier = komodo.prettier:prettier_main',
            ]
        }
)
