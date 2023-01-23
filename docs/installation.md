# Installation

The tool is not hosted on PyPI but can be installed with `pip` directly from GitHub:

```bash
pip install git+https://github.com/equinor/komodo.git
```

Developers should clone the repository, then change to its directory and also install everything in `dev-requirements.txt`:

```bash
pip install -r dev-requirements.txt
```

During development you can do the following for an "editable" install that changes while you develop:

```bash
pip install -e .
```

If you want to help develop `komodo`, please read [Development](development.md).
