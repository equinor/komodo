# Komodo commands

The main command is `kmd`. This command builds and installs environments. See [Basic Usage](basic-usage.md).

As well as the `kmd` command, this package installs several other
commands, each with its own options:

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
