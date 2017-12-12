# Komodo --- Software Innovation Bergen Software Distribution

Komodo is a software distribution system.

The purpose of Komodo is to be able to automatically, reproducibly, testably
create a software distribution containing all systems Software Innovation Bergen
is responsible for.  Automatic deploy of new releases as well as nightly deploy
and the option of automatically moving the testing stage will be supported.

## Overall goal

We have a repository of packages.  Each package contains
* a list of versions
* dependencies
* source
* build information
* maintainer information

The repository.yml may look like this:

```yml
boost:
  version: 1.60
  rpm: path
opm-parser:
  version: 1.2.0
  depends:
    - ecl
    - boost
  git: git@github.com:opm/opm-parser
ecl:
  version: 2.3
  git: git@github.com:statoil/libecl
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
