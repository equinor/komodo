# Komodo
[![Build Status](https://github.com/equinor/komodo/actions/workflows/test.yml/badge.svg)](https://github.com/equinor/komodo/actions/workflows/test.yml)

## Software Innovation Bergen Software Distribution

Komodo is a software distribution system.

The purpose of Komodo is to be able to automatically, reproducibly, testably
create a software distribution. Automatic deploy of new releases as well as
nightly deploy and the option of automatically moving the testing stage will be
supported.

## Overall goal

We have a repository of packages. Each package contains
* a list of versions
* dependencies
* source
* build information
* maintainer information

The repository.yml may look like this:

```yml
ert:
  version: 2.17
  source: pypi
  make: pip
opm-parser:
  version: 1.2.0
  depends:
    - ecl
    - boost
  git: git@github.com:opm/opm-parser
ecl:
  version: 2.3
  git: git@github.com:equinor/ecl
```

Then a release, e.g. _unstable_ is defined as another YAML file,
e.g. `unstable.yml`, containing

```yml
boost: 1.60
opm-parser: 1.2.0
ecl: 2.3
```

A full software distribution can then be built and deployed to a specified path,
e.g. `/my/software/center/unstable`.

To use, `source /my/software/center/unstable/enable`.

## Auto-formatting configuration files

You can auto-format repository and/or releases by running something like
```bash
komodo-clean-repository prettier --files repository.yml releases/*
```
If you are in e.g CI and only want to check style compliance, add `--check`.

## Finding reverse dependecies

You can show reverse dependencies of a package by running the tool `komodo-reverse-deps`:
```bash
komodo-reverse-deps releases/matrices/2022.09.02.yml repository.yml --pkg websockets
```
If `--pkg` is not specified, the program will prompt for it.

### Render graph

Can also output a graph of the reverse dependencies in dot format which can then be rendered using
the dot program from the `ImageMagick` package. As a convenience can also render it automatically
using dot and display. To use this convenience you must have installed these tools, which are
distributed with the Graphviz and ImageMagick packages.

## Install

```bash
pip install git+https://github.com/equinor/komodo.git
```

## Run tests

```bash
git clone https://github.com/equinor/komodo.git
cd komodo
pip install -r dev-requirements.txt
pytest tests
```
