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
    test_suite="tests",
    install_requires=["shell", "PyYAML", "ruamel.yaml", "packaging", "PyGithub"],
    entry_points={
        "console_scripts": [
            "kmd = komodo.cli:cli_main",
            "komodo-check-symlinks = komodo.symlink.sanity_check:sanity_main",
            "komodo-create-symlinks = komodo.symlink.create_links:symlink_main",
            "komodo-lint = komodo.lint:lint_main",
            "komodo-non-deployed = komodo.deployed:deployed_main",
            "komodo-suggest-symlinks = komodo.symlink.suggester.cli:main",
            "komodo-extract-dep-graph = komodo.extract_dep_graph:main",
            "komodo-lint-package-status = komodo.lint_package_status:main",
            "komodo-lint-maturity = komodo.lint_maturity:main",
            'komodo-clean-repository = komodo.release_cleanup:main',
            'komodo-transpiler = komodo.release_transpiler:main',
        ]
    },
)
