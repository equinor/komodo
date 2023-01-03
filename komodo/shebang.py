import os

from komodo.shell import shell


def _is_shebang(s):
    """Checks if the string potentially is a Python shebang."""
    return s.startswith("#!/") and "python" in s


def fixup_python_shebangs(prefix, release):
    """Fix shebang to $PREFIX/bin/python.

    Some packages installed with pip do not respect target executable, that is,
    they set as their shebang executable the Python executabl used to build the
    komodo distribution with instead of the Python executable that komodo
    deploys.  This breaks the application since the corresponding Python modules
    won't be picked up correctly.

    For now, we use sed to rewrite the first line in some executables.

    This is a hack that should be fixed at some point.

    """
    binpath = os.path.join(prefix, release, "root", "bin")
    if not os.path.isdir(binpath):
        # No bin files to fix
        return
    python_ = os.path.join(binpath, "python")

    bins_ = []
    # executables with wrong shebang
    for bin_ in os.listdir(binpath):
        try:
            with open(os.path.join(binpath, bin_), "r") as f:
                shebang = f.readline().strip()
            if _is_shebang(shebang):
                bins_.append(bin_)
        except Exception as err:
            print(f"Exception in reading bin {bin_}: {err}")

    for bin_ in bins_:
        binpath_ = os.path.join(prefix, release, "root", "bin", bin_)
        if os.path.exists(binpath_):
            shell(f"""sed -i 1c#!{python_} {binpath_}""")
