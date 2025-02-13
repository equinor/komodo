# Komodo

[![Build Status](https://github.com/equinor/komodo/actions/workflows/test.yml/badge.svg)](https://github.com/equinor/komodo/actions/workflows/test.yml)

Komodo is a software distribution system.

The purpose of Komodo is to automatically, reproducibly, and testably create a
software distribution. Automatic deploy of new releases, as well as nightly
deploy and the option of automatically moving the testing stage, is supported.


## Install

The tool is not hosted on PyPI but can be installed with `pip` directly from
GitHub:

```bash
pip install git+https://github.com/equinor/komodo.git
```

## Documentation

[The documentation](https://equinor.github.io/komodo) is online. 
Developers can build it by installing with dev-dependencies by running `pip install ".[dev]"` and running `make html` in the `docs` directory.


## Basic usage

We have a 'repository' of packages described in a
[YAML](https://yaml.org/) file. Each package contains a list of one or more
versions. Each version contains:

* Build information.
* Maintainer.
* Source, e.g. PyPI or a GitHub repository, if required.
* Dependency list, if any.
* Other metadata, depending on the type of package.

For example, we may have a `repository.yml` like this:

```yaml
python:
  3-builtin:
    make: sh
    makefile: build__python-virtualenv.sh
    maintainer: foo@example.com
    makeopts: --virtualenv-interpreter python3

treelib:
  1.6.1:
    source: pypi
    make: pip
    maintainer: bar@example.com
    depends:
      - python
```

Note that `build__python-virtualenv.sh` is a script that comes with `komodo`
(in `komodo/data`); it will use the system Python in the environment it builds.

Now a 'release', e.g. _stable_, is defined in another YAML file, e.g.
`stable.yml`, containing some or all of the packages in the repository file:

```yaml
python: 3-builtin
treelib: 1.6.1
```

A full software distribution can then be built and deployed to a specified
path, e.g. `./builds/stable-0.0.1`, with the following command:

```bash
kmd stable.yml repository.yml --prefix builds --release stable-0.0.1
```

To use this environment, type `source builds/stable-0.0.1/enable`.


## Other komodo commands

As well as the `kmd` command, this package installs several other
commands, each with its own options:

- `komodo-ask-for-tags` &mdash; Checks if there are any internal dependencies
  with changes since last release and composes a message to ask for new tags
  from the respective maintainers
- `komodo-check-symlinks` &mdash; Verify symlinks for komodo versions are
according to a given config
- `komodo-check-pypi` &mdash; Checks if pypi packages are up to date
- `komodo-clean-repository` &mdash; Clean up unused versions in the repository
file based on a set of releases
- `komodo-create-symlinks` &mdash; Create symlinks for komodo versions
- `komodo-extract-dep-graph` &mdash; Extracts dependencies from a given set of
packages
- `komodo-insert-proposals` &mdash; Copy proposals into release and create PR
- `komodo-lint` &mdash; Lint komodo setup
- `komodo-lint-maturity` &mdash; Lint the maturity of packages
- `komodo-lint-package-status` &mdash; Lint the package status file
- `komodo-lint-upgrade-proposals` &mdash; Lint the upgrade proposals file against
the repository file
- `komodo-non-deployed` &mdash; Outputs the name of undeployed matrices given
an installation root and a release folder
- `komodo-post-messages` &mdash; Post messages to a release
- `komodo-reverse-deps` &mdash; Extracts dependencies from a given set of
packages
- `komodo-show-version` &mdash; Return the version of a specified package in the active release
- `komodo-snyk-test` &mdash; Test a release for security and license issues
- `komodo-suggest-symlinks` &mdash; Returns a pull request if the symlink
configuration could be updated
- `komodo-transpiler` &mdash; Build release files


## Run tests

In a virtual environment:

```bash
git clone https://github.com/equinor/komodo.git
cd komodo
pip install ".[dev]"
pytest tests
```
