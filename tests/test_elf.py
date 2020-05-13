import sys
import subprocess
import re
import os
import shutil
from komodo import elf


# NOTE: If these tests are failing, know that they're meant for AMD64 Linux
# machines only. If we're testing komodo on a different CPU architecture or OS
# kernel, these will need to be updated.


def _compile(args, code="int main() {}\n"):
    with open("main.c", "w") as f:
        f.write(code)
    assert subprocess.call(re.split(r"\s+", args.format(code="main.c"))) == 0


def _make_executable(dest):
    _compile("gcc -o{} {{code}}".format(dest))


def _make_shared_object(dest):
    _compile("gcc -shared -fPIC -o{} {{code}}".format(dest))


def _make_text_file(dest):
    with open(dest, "w") as f:
        f.write("#!/usr/bin/python\nprint('Hello\n')")


def test_exec():
    """Check whether Python is a valid executable (Hint: it is)"""
    assert elf.is_valid_elf_file(os.path.realpath(sys.executable))


def test_dyn(tmpdir):
    """Compile a shared object and test it"""
    with tmpdir.as_cwd():
        _compile("gcc -shared {code}")

        assert os.path.isfile("a.out")
        assert elf.is_valid_elf_file("a.out")


def test_symlink(tmpdir):
    """Symlinks may point to ELF files outside of the komodo release, so it is
    imperative that we do not touch them

    """
    with tmpdir.as_cwd():
        os.symlink("/bin/bash", "symlink")

        assert os.path.isfile("symlink")
        assert not elf.is_valid_elf_file("symlink")


def test_object_file(tmpdir):
    """Object files (.o) are ELF, but contain no linking information"""
    with tmpdir.as_cwd():
        _compile("gcc -c -omain.o {code}")

        assert os.path.isfile("main.o")
        assert not elf.is_valid_elf_file("main.o")


def test_incorrect_arch(tmpdir):
    """We only support amd64 CPU architecture. We test an x86 binary compiled with
    the m32 flag

    """
    with tmpdir.as_cwd():
        _compile("gcc -m32 {code}")

        assert os.path.isfile("a.out")
        assert not elf.is_valid_elf_file("a.out")


def test_patch(tmpdir):
    """We test the patching functionality by a shared object (liba.so) and an
    executable (a.out). The executable links to liba.so, where the function 'a'
    is located

    """
    with tmpdir.as_cwd():
        _compile("gcc -shared -fPIC -oliba.so {code}", code="int a(){return 42;}")
        _compile("gcc {code} -L. -la", code="int main(){return a();}")

        assert os.path.isfile("liba.so")
        assert os.path.isfile("a.out")

        # Program returns -1 (127) because it can't find the library
        assert subprocess.call(["./a.out"]) == 127

        # Program returns 42 as expected when we patchelf
        elf.patch("a.out", os.getcwd(), os.environ.get("PATCHELF_EXEC", "patchelf"))
        assert subprocess.call(["./a.out"]) == 42


def test_patch_with_existing_rpath(tmpdir):
    """When shipping portable binaries it is imperative to set the RPATH so that
    your portable binary is able to locate any of its dependencies. Thus, it is
    normal to find executables with '$ORIGIN/lib' or '$ORIGIN/../lib' as their
    RPATH. '$ORIGIN' is a magic string that tells the linker (default:
    '/usr/lib/ld-linux.so.2') to replace it with the directory in which the
    executable resides.

    This is also common in PyPI packages with binary wheels, and thus is very
    important that we support it.

    We test this by creating two libraries: liba.so and libb.so. The first
    exists in our $PWD, and the second exists in $PWD/lib. The first simulates
    a system-installed library while the second simulates a portably-shipped
    library. 'a.out' uses both libraries, but has information about where to
    find 'libb.so' only

    """
    with tmpdir.as_cwd():
        tmpdir.mkdir("lib")
        _compile("gcc -shared -fPIC -oliba.so {code}", code="int a(){return 1;}")
        _compile("gcc -shared -fPIC -olib/libb.so {code}", code="int b(){return 2;}")
        _compile(
            "gcc {code} -Wl,-rpath,$ORIGIN/lib -L. -L./lib -la -lb",
            code="int main(){return a()+b();}",
        )

        assert os.path.isfile("liba.so")
        assert os.path.isfile("lib/libb.so")
        assert os.path.isfile("a.out")

        # Program returns -1 (127) because it can't find liba.so
        assert subprocess.call(["./a.out"]) == 127

        # Program succeeds because we have specified LD_LIBRARY_PATH
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.getcwd()
        assert subprocess.call(["./a.out"], env=env) == 3

        # Program succeeds when we patchelf because it prepends the RPATH
        elf.patch("a.out", os.getcwd(), os.environ.get("PATCHELF_EXEC", "patchelf"))
        assert subprocess.call(["./a.out"]) == 3


def test_find_elfs(tmpdir):
    """Create a fake release tree and test that we're collecting the right files"""
    bins = ["bin/bash", "bin/python"]
    libs = ["lib/libpython3.6.so", "lib/python3.6/site-packages/a/.libs/libz.so"]
    syms = {"bin/python3": "bin/python", "usr/bin": "/bin"}
    txts = ["bin/pytest", "lib/python3.6/site-packages/a/__init__.py"]

    with tmpdir.as_cwd():
        # Make directories
        for path in bins + libs + list(syms) + txts:
            dir = os.path.dirname(path)
            if not os.path.isdir(dir):
                os.makedirs(dir)

        # Make files
        for bin_ in bins:
            _make_executable(bin_)
        for lib in libs:
            _make_shared_object(lib)
        for src, dst in syms.items():
            os.symlink(dst, src)
        for txt in txts:
            _make_text_file(txt)

        expect = set(map(os.path.abspath, bins + libs))
        elfs = elf.list_elfs(os.getcwd())
        assert set(elfs) == expect
