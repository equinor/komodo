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

```yml
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

```yml
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
- `komodo-check-pypi` &mdash; Checks if pypi packages are up to date
- `komodo-insert-proposals` &mdash; Copy proposals into release and create PR
- `komodo-post-messages` &mdash; Post messages to a release
- `komodo-check-symlinks` &mdash; Verify symlinks for komodo versions are
according to a given config
- `komodo-lint` &mdash; Lint komodo setup
- `komodo-reverse-deps` &mdash; Extracts dependencies from a given set of
packages
- `komodo-clean-repository` &mdash; Clean up unused versions in the repository
file based on a set of releases
- `komodo-lint-maturity` &mdash; Lint the maturity of packages
- `komodo-snyk-test` &mdash; Test a release for security and license issues
- `komodo-create-symlinks` &mdash; Create symlinks for komodo versions
- `komodo-lint-package-status` &mdash; Lint the package status file
- `komodo-suggest-symlinks` &mdash; Returns a pull request if the symlink
configuration could be updated
- `komodo-extract-dep-graph` &mdash; Extracts dependencies from a given set of
packages
- `komodo-non-deployed` &mdash; Outputs the name of undeployed matrices given
an installation root and a release folder
- `komodo-transpiler` &mdash; Build release files
- `komodo-show-version` &mdash; Return the version of a specified package in the active release

### Auto-formatting configuration files

You can auto-format repository and/or releases by running something like

```bash
komodo-clean-repository prettier --files repository.yml releases/*
```

If you are in e.g. CI and only want to check style compliance, add `--check`.

### Finding reverse dependecies

You can show reverse dependencies of a package by running the tool
`komodo-reverse-deps`:

```bash
komodo-reverse-deps releases/matrices/2022.09.02.yml repository.yml --pkg websockets
```

If `--pkg` is not specified, the program will prompt for it.

The `--dot` option outputs the reverse dependency graph in `.dot` format.
Alternatively, if `GraphViz` and `ImageMagick` are available, the
`--display_dot` option will try to render the graph directly.


## Run tests

```bash
git clone https://github.com/equinor/komodo.git
cd komodo
pip install -r dev-requirements.txt
pytest tests
```
