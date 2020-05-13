import os
import subprocess
import six
from komodo.shell import shell


def is_valid_elf_file(path):
    """Checks whether a given file is a valid amd64 Linux ELF file that is either
    an executable or a dynamic library that we can patch.

    """
    if not os.path.isfile(path) or os.path.islink(path):
        return False

    with open(path, "rb") as f:
        # First 16 bytes are the E_IDENT section of the ELF header. The 4 next
        # bytes are two uint16_t's representing E_TYPE and E_MACHINE.
        headstr = f.read(20)

    # Check magic string
    if len(headstr) != 20 or headstr[:4] != b"\x7fELF":
        return False
    if six.PY2:
        head = tuple(map(ord, headstr))
    else:
        head = headstr

    # EI_CLASS must be ELFCLASS64 = 2 (64-bit registers)
    if head[4] != 2:
        return False
    # EI_DATA must be ELFDATA2LSB = 1 (Little-Endian, two's complement)
    if head[5] != 1:
        return False
    # EI_VERSION must be 1 (the only one that exists at time of writing)
    if head[6] != 1:
        return False
    # EI_OSABI must be either ELFOSABI_SYSV = 0 or ELFOSABI_GNU = 3
    # (GNU/Linux). Seems like some distros prefer SYSV (Debian) while others
    # prefer to specify GNU (RHEL). Either works for us.
    if head[7] != 0 and head[7] != 3:
        return False
    # We ignore EI_ABIVERSION
    # The rest of the E_IDENT section is padding

    # e_type must be either ET_EXEC = 2 (executable binary) or ET_DYN = 3
    # (shared library). These are uint16_t's, and we have assumed ELFDATA2LSB,
    # which is Little-Endian, so these byte-strings are little-endian.
    e_type    = headstr[16:18]
    if e_type != b"\x02\0" and e_type != b"\x03\0":
        return False

    # Machine architecture. For safety we allow only EM_X86_64 = 62 (amd64).
    # Again, this is a uint16_t, so bytes are encoded as little-endian.
    e_machine = headstr[18:20]
    if e_machine != b"\x3e\0":
        return False

    # We don't care about the rest of the header, since it deals with positions
    # of different data sections within the file and other nonsense.
    return True


def list_elfs(path):
    """List all patchable ELF files in a directory and its subdirectories."""
    for root, _dirs, files in os.walk(path):
        for fn in files:
            elf = os.path.join(root, fn)
            if is_valid_elf_file(elf):
                yield elf


def patch(path, libdir, patchelf="patchelf"):
    """Patch a single ELF file by appending the new RPATH to the old RPATH, if any,
    using patchelf

    """
    rpath = libdir
    proc = subprocess.Popen([patchelf, "--print-rpath", path], stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    if six.PY2:
        old_rpath = str(stdout.strip(), encoding="ascii")
    else:
        old_rpath = stdout.strip()
    if len(old_rpath) > 0:
        rpath = "{}:{}".format(old_rpath, rpath)

    shell("{} --set-rpath {} {}".format(patchelf, rpath, path))


def patch_all(root, libdir, patchelf="patchelf"):
    """Patch all patchable ELF files so that libdir is part of their RPATH"""
    for path in list_elfs(root):
        patch(path, libdir, patchelf)
