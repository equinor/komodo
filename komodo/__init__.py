"""Komodo software distribution build system."""

import os

from .build import make, pypaths
from .fetch import fetch
from .shell import shell, pushd
from .lint import lint
from .cleanup import cleanup
from .maintainer import maintainers


def _is_shebang(s):
    """Checks if the string potentially is a Python shebang."""
    return s.startswith('#!/') and 'python' in s


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
    binpath = os.path.join(prefix, release, 'root', 'bin')
    python_ = os.path.join(binpath, 'python')

    bins_ = []
    # executables with wrong shebang
    for bin_ in os.listdir(binpath):
        try:
            with open(os.path.join(binpath, bin_), 'r') as f:
                shebang = f.readline().strip()
            if _is_shebang(shebang):
                bins_.append(bin_)
        except Exception as err:
            print('Exception in reading bin: %s' % err)

    sedfxp = """sed -i 1c#!{0} {1}"""
    for bin_ in bins_:
        binpath_ = os.path.join(prefix, release, 'root', 'bin', bin_)
        if os.path.exists(binpath_):
            shell(sedfxp.format(python_, binpath_))


# We are typically comparing the filesystem structure on two different
# filesystems, then it seems that both the os.walk() and the dnames and fnames
# lists come in different order, that is the reason we sort everything.
def tree_hash(path):
    entries = []
    tail = path.split("/")[-1]
    path_offset = len(path) - len(tail)
    for d,dnames,fnames in os.walk(path):
        root = d[path_offset:]
        # It seems the .dist-info directories from pip installed pacakges are
        # not equal in the final installation directory and the fakeroot
        # installation directory. These driectories are therefor skipped here,
        # otehrwise the tree_equal() function will always return False.
        if root.endswith(".dist-info"):
            continue

        entries.append((root , {"files" : sorted(fnames),
                                "directories" : sorted(dnames)}))
    return hash(str(sorted(entries)))


def tree_equal(path1, path2):
    return tree_hash(path1) == tree_hash(path2)


__version__ = '1.0'
__author__ = 'Software Innovation Bergen, Statoil ASA'

__copyright__ = 'Copyright 2017, Statoil ASA'
__license__ = 'GNU General Public License, version 3 or any later version'

__credits__ = __author__
__maintainer__ = __author__
__email__ = 'fg_gpl@statoil.com'
__status__ = 'Production'

__ALL__ = ['make', 'fetch', 'shell', 'lint', 'maintainers']
