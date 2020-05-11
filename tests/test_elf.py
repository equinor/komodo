import sys
import subprocess
import re
import os
import shutil
from komodo import is_valid_elf_file


# NOTE: If these tests are failing, know that they're meant for AMD64 Linux
# machines only. If we're testing komodo on a different CPU architecture or OS
# kernel, these will need to be updated.


def _compile(args, code="int main() {}\n"):
    with open("main.c", "w") as f:
        f.write(code)
    assert subprocess.call(re.split(r"\s+", args.format(code="main.c"))) == 0


def test_exec():
    """Check whether Python is a valid executable (Hint: it is)"""
    assert is_valid_elf_file(sys.executable)


def test_elf_symlink(tmpdir):
    """We don't like symlinks here"""
    with tmpdir.as_cwd():
        os.symlink("/bin/bash", "symlink")

        assert os.path.isfile("symlink")
        assert not is_valid_elf_file("symlink")


def test_dyn(tmpdir):
    """Compile a dynamic library and test it"""
    with tmpdir.as_cwd():
        _compile("gcc -shared {code}")

        assert os.path.isfile("a.out")
        assert is_valid_elf_file("a.out")


def test_object_file(tmpdir):
    """Object files (.o) are ELF, but contain no linking information"""
    with tmpdir.as_cwd():
        _compile("gcc -c -omain.o {code}")

        assert os.path.isfile("main.o")
        assert not is_valid_elf_file("main.o")


def test_incorrect_arch(tmpdir):
    """We only support amd64 CPU architecture. We test an x86 binary compiled with the m32 flag"""
    with tmpdir.as_cwd():
        _compile("gcc -m32 {code}")

        assert os.path.isfile("a.out")
        assert not is_valid_elf_file("a.out")


def test_patch(tmpdir):
    with tmpdir.as_cwd():
        _compile("gcc -shared -fPIC -oliba.so {code}", code="int a(){return 42;}")
        _compile("gcc {code} -L. -la", code="int main(){return a();}")

        assert os.path.isfile("liba.so")
        assert os.path.isfile("a.out")

        # Program returns -1 (127) because it can't find the library
        assert subprocess.call(["./a.out"]) == 127

        # Program returns 42 as expected when we patchelf
        assert subprocess.call(["patchelf", "--set-rpath", os.getcwd(), "a.out"]) == 0
        assert subprocess.call(["./a.out"]) == 42


def test_patch_with_existing_rpath(tmpdir):
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
        rpath = "{}:$ORIGIN/lib".format(os.getcwd())
        assert subprocess.call(["patchelf", "--set-rpath", rpath, "a.out"])
        assert subprocess.call(["./a.out"]) == 3


def test_find_elfs(tmpdir):
    bins = ("bin/bash", "bin/python")
    libs = ("lib/libpython3.6.so", "lib/python3.6/site-packages/a/.libs/libz.so")
    txts = ("bin/pytest", "lib/python3.6/site-packages/a/__init__.py")

    with tmpdir.as_cwd():
        for bin_ in bins:
            tmpdir.mkdir(os.path.dirname(bin_))
            shutil.copyfile(sys.executable, bin_)
        for lib in libs:
            pass
        for txt in txts:
            with open(txt, "w") as f:
                f.write("#!/usr/bin/env python\nprint('Hi!')\n")

        elfs = elf.find_all(os.getcwd(), "bleeding-py36")
        assert set(elfs) == set(bins + libs)
