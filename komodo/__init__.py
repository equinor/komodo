"""Komodo software distribution build system."""

import os
import glob
import struct

from .build import make, pypaths
from .fetch import fetch
from .shell import shell, pushd
from .lint import lint
from .prettier import prettier
from .cleanup import cleanup
from .maintainer import maintainers


def _is_shebang(s):
    """Checks if the string potentially is a Python shebang."""
    return s.startswith('#!/') and 'python' in s


def is_valid_elf_file(path):
    """Checks whether a given file is a valid amd64 Linux ELF file that is either
    an executable or a dynamic library that we can patch.

    """
    if not os.path.isfile(path) or os.path.islink(path):
        return False

    with open(path, "rb") as f:
        # First 16 bytes are the E_IDENT section of the ELF header. The 4 next
        # bytes are two uint16_t's representing E_TYPE and E_MACHINE.
        head = f.read(20)

    # Check magic string
    if len(head) != 20 or head[:4] != b"\x7fELF":
        return False

    # EI_CLASS must be ELFCLASS64 = 2 (amd64)
    if head[4] != b"\x02":
        return False
    # EI_DATA must be ELFDATA2LSB = 1 (Little-Endian, two's complement)
    if head[5] != b"\x01":
        return False
    # EI_VERSION must be 1 (the only one that exists at time of writing)
    if head[6] != b"\x01":
        return False
    # EI_OSABI must be either ELFOSABI_SYSV = 0 or ELFOSABI_GNU = 3
    # (GNU/Linux). Seems like some distros prefer SYSV (Debian) while others
    # prefer to specify GNU (RHEL). Either works for us.
    if head[7] != b"\0" and head[7] != b"\x03":
        return False
    # We ignore EI_ABIVERSION
    # The rest of the E_IDENT section is padding

    # e_type must be either ET_EXEC = 3 (executable binary) or ET_DYN = 4
    # (shared library). These are uint16_t's, and we have assumed ELFDATA2LSB,
    # which is Little-Endian, so these byte-strings are little-endian.
    e_type    = head[16:18]
    if e_type != b"\x03\0" and e_type != b"\x04\0":
        return False

    # Machine architecture. For safety we allow only EM_X86_64 = 62 (amd64).
    # Again, this is a uint16_t, so bytes are encoded as little-endian.
    e_machine = head[18:20]
    if e_machine != b"\x3e\0":
        return False

    # We don't care about the rest of the header, since it deals with positions
    # of different data sections within the file and other nonsense.
    return True


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


def fixup_rpaths(prefix, release, patchelf):
    """TODO: Explain"""
    release_root = os.path.join(prefix, release, "root")
    rpath = "{0}/lib:{0}/lib64".format(release_root)

    for root, _dirs, files in os.walk(release_root):
        for fn in files:
            try:
                with open(fn, "rb") as f:
                    if f.read(4) != b"\x7fELF":
                        continue
            except IOError:
                continue
            prog = os.path.join(root, fn)
            shell("{} \"--set-rpath={}\" \"{}\"".format(patchelf, rpath, prog))


def strip_version(version):
    """
    In order to be able to support both py2 and py3 we need to be able
    to have multiple versions of the same package/version due to
    differences in dependencies. This is achieved by adding i.e '+py3'
    to a version-spec in both the release and repository file. This func
    strips the '+' and everything behind for all pip packages so we are 
    able to install.
    """
    return version.split("+")[0]


__version__ = '1.0'
__author__ = 'Software Innovation Bergen, Statoil ASA'

__copyright__ = 'Copyright 2017, Statoil ASA'
__license__ = 'GNU General Public License, version 3 or any later version'

__credits__ = __author__
__maintainer__ = __author__
__email__ = 'fg_gpl@statoil.com'
__status__ = 'Production'

__ALL__ = ['make', 'fetch', 'shell', 'lint', 'maintainers']
