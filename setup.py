#!/usr/bin/env python
from __future__ import print_function

from setuptools import setup

setup(
    name="Komodo",
    version="1.0",
    packages=["komodo", "komodo.symlink", "komodo.symlink.suggester"],
    package_dir={
        "komodo": "komodo",
        "komodo.symlink": "komodo/symlink",
        "komodo.symlink.suggester": "komodo/symlink/suggester",
    },
    scripts=["bin/kmd"],
    test_suite="tests",
    install_requires=["shell", "PyYAML", "ruamel.yaml", "PyGithub"],
    entry_points={
        "console_scripts": [
            "komodo-check-symlinks = komodo.symlink.sanity_check:sanity_main",
            "komodo-create-symlinks = komodo.symlink.create_links:symlink_main",
            "komodo-lint = komodo.lint:lint_main",
            "komodo-non-deployed = komodo.deployed:deployed_main",
            "komodo-prettier = komodo.prettier:prettier_main",
            "komodo-suggest-symlinks = komodo.symlink.suggester.cli:main",
        ]
    },
)
