# Development

If you'd like to develop `komodo`, this page should help you get started.


## Installation

See [Installation](installation.md).


## Contributing

If you'd like to contribute pull requests back to the main `komodo ` project, please see [`CONTRIBUTING.md`](https://github.com/equinor/komodo/blob/main/CONTRIBUTING.md).


## Testing

After installing the development reqiurements you can run the tests from the main directory with:

    pytest tests


## Building the package

This repo uses PEP 518-style packaging. [Read more about this](https://setuptools.pypa.io/en/latest/build_meta.html) and [about Python packaging in general](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

Building the project requires `build`, so first:

    python -m pip install build

Then to build `komodo` locally:

    python -m build

This builds both `.tar.gz` and `.whl` files, either of which you can install with `pip`.


## Building the docs

You can build the docs with the following commands:

    cd docs
    make html

There is a continuous integration script to update the docs on published releases.


## Continuous integration

This repo has GitHub 'workflows' or 'actions'. Check [GitHub](https://github.com/equinor/komodo/actions) to see what is running.
