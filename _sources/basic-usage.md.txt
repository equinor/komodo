# Basic usage

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
