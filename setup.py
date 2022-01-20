from __future__ import print_function

from setuptools import setup

setup(
    name="Komodo",
    version="1.0",
    packages=["komodo", "komodo.data", "komodo.symlink", "komodo.symlink.suggester"],
    package_data={"komodo.data": ["*"],},
    package_dir={
        "komodo": "komodo",
        "komodo.data": "komodo/data",
        "komodo.symlink": "komodo/symlink",
        "komodo.symlink.suggester": "komodo/symlink/suggester",
    },
    test_suite="tests",
    install_requires=[
        "shell",
        "PyYAML",
        "ruamel.yaml",
        "packaging",
        "PyGithub >= 1.55",
        "jinja2",
        "pysnyk @ git+https://github.com/equinor/pysnyk ; python_version >= '3.7'",
    ],
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
            'komodo-post-messages = komodo.post_messages:main',
            'komodo-snyk-test = komodo.snyk_reporting:main',
            'komodo-reverse-deps = komodo.reverse_dep_graph:main',
            'komodo-insert-proposals = komodo.insert_proposals:main',
            'komodo-check-pypi = komodo.check_up_to_date_pypi:main',
        ]
    },
)
