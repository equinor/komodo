import os
import pytest
import subprocess
from komodo.shim import create_shims, shim_template
from textwrap import dedent
from pathlib import Path


binfiles = {
    "test": "Testfile",
    "foo": "bar",
    "python": dedent("""\
        #!/bin/bash
        # This is totally a python file
        exit 42
    """)
}


def setup_bindir(tmpdir):
    (tmpdir / "bin").mkdir()

    for name, text in binfiles.items():
        path = str(tmpdir / "bin" / name)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, 0o755)


def test_shims_created(tmpdir):
    with tmpdir.as_cwd():
        setup_bindir(tmpdir)
        bin_path = str(tmpdir / "bin")
        libexec_path = str(tmpdir / "libexec")

        # Check that files were created
        assert set(binfiles.keys()) == set(os.listdir(bin_path))

        create_shims(str(tmpdir))
        assert set(binfiles.keys()) == set(os.listdir(bin_path))
        assert set(binfiles.keys()) == set(os.listdir(libexec_path))


def test_libexec_are_binfiles(tmpdir):
    with tmpdir.as_cwd():
        setup_bindir(tmpdir)
        libexec_path = str(tmpdir / "libexec")

        create_shims(str(tmpdir))
        for name in os.listdir(libexec_path):
            with open(os.path.join(libexec_path, name)) as f:
                assert binfiles[name] == f.read()


def test_bin_are_shims(tmpdir):
    with tmpdir.as_cwd():
        setup_bindir(tmpdir)
        bin_path = str(tmpdir / "bin")

        create_shims(str(tmpdir))
        for name in os.listdir(bin_path):
            with open(os.path.join(bin_path, name)) as f:
                assert shim_template == f.read()


def test_executable(tmpdir):
    with tmpdir.as_cwd():
        setup_bindir(tmpdir)

        subprocess.check_output


@pytest.mark.parametrize("libdir", ["lib", "lib64"])
def test_lib(tmpdir, libdir):
    c_src = 'const char *foo() { return "bar"; }'
    py_src = dedent("""\
        #!/usr/bin/env python
        import sys
        from ctypes import CDLL, c_char_p
        lib = CDLL("libfoo.so")
        foo = lib.foo
        foo.restype = c_char_p
        if foo() != b"bar":
            sys.exit(1)
    """)

    with tmpdir.as_cwd():
        with open("lib.c", "w") as f:
            f.write(c_src)

        (tmpdir / libdir).mkdir()
        subprocess.call(["cc", "-shared", f"-o{libdir}/libfoo.so", "lib.c", "-fPIC"])

        # Create test script
        test_path = Path(tmpdir / "bin" / "test")
        test_path.parent.mkdir()
        test_path.write_text(py_src, encoding="ascii")
        test_path.chmod(0o755)

        create_shims(str(tmpdir))

        # Calling test directly should fail
        assert subprocess.call(["libexec/test"]) == 1

        # Calling via shim should succeed
        assert subprocess.call(["bin/test"]) == 0
