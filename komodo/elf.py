import os
import subprocess
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
        head = f.read(20)

    # Check magic string
    if len(head) != 20 or head[:4] != b"\x7fELF":
        return False

    # EI_CLASS must be ELFCLASS64 = 2 (64-bit registers)
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


def list_elfs(path):
    for root, _dirs, files in os.walk(path):
        for fn in files:
            elf = os.path.join(root, fn)
            if is_valid_elf_file(elf):
                yield elf


def patch(path, libdir, patchelf="patchelf"):
    rpath = libdir
    proc = subprocess.Popen([patchelf, "--print-rpath", path], stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    old_rpath = stdout.strip()
    if len(old_rpath) > 0:
        rpath = "{}:{}".format(old_rpath, rpath)

    shell("{} --set-rpath {} {}".format(patchelf, rpath, path))


def patch_all(root, libdir, patchelf="patchelf"):
    for path in list_elfs(root):
        patch(path, libdir, patchelf)
