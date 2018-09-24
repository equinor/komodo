"""Komodo software distribution build system."""

import os
import time

from .build import make, pypaths
from .fetch import fetch
from .shell import shell, pushd
from .lint import lint
from .cleanup import cleanup
from .maintainer import maintainers
from .link import update_links

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


__version__ = '1.0'
__author__ = 'Software Innovation Bergen, Statoil ASA'

__copyright__ = 'Copyright 2017, Statoil ASA'
__license__ = 'GNU General Public License, version 3 or any later version'

__credits__ = __author__
__maintainer__ = __author__
__email__ = 'fg_gpl@statoil.com'
__status__ = 'Production'

__ALL__ = ['make', 'fetch', 'shell', 'lint', 'maintainers', 'update_links']




# In the filesystem the release 'xxx' is located under the directory
# $PREFIX/xxx-$timestamp and the actual release is found through a symlink:
#
#     $PREFIX/xxx -> xxx-$timestamp
#
# The timestamp is unix timestamp - seconds since the 1970 epoch. The functions
# make_release_name() and split_release_name() will construct and deconstruct
# such a directory name:
#
# make_release_link('2018.03')             -> '2018.03-1537801167'
# split_release_link('2018.03-1537801167') -> '2018.03', 1537801167
#
# Observe that the split_release_link will convert the string represantation to
# int. If the split_release_link fails it will return None in the second
# argument.


def make_release_name(release):
    return '{}-{:012}'.format(release, int(time.mktime( time.localtime())) )


def split_release_name(name):
    tmp = name.split('-')
    if len(tmp) == 1:
        return name, None

    try:
        seconds = int(tmp[-1])
    except ValueError:
        seconds = None

    return '-'.join(tmp[:-1]), seconds
