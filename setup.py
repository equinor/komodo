#!/usr/bin/env python
from __future__ import print_function

from setuptools import setup

setup(
    name='Komodo',
    version='1.0',
    packages=['komodo', 'komodo.symlink'],
    package_dir={'komodo' : 'komodo', 'komodo.symlink': 'komodo/symlink'},
    scripts=['bin/kmd'],
    test_suite='tests',
    install_requires=['shell', 'PyYAML', 'ruamel.yaml'],
    entry_points={
        'console_scripts': [
            'komodo-lint = komodo.lint:lint_main',
            'komodo-prettier = komodo.prettier:prettier_main',
            'komodo-create-symlinks = komodo.symlink.create_links:symlink_main',
            'komodo-check-symlinks = komodo.symlink.sanity_check:sanity_main',
            ]
        }
)
