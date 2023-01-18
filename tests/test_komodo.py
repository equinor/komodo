import os

from komodo.shebang import fixup_python_shebangs


def test_fixup_python_shebangs(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support

    prefix = os.path.join(tmpdir, "prefix")
    bindir = os.path.join(prefix, "release/root/bin")
    os.makedirs(bindir)
    with open(os.path.join(bindir, "bad_shebang"), "w") as f:
        f.write("#!/wildly/wrong/path/to\xe7\x8e\xa9/python\n")

    fixup_python_shebangs(prefix, "release")

    target = "#!{}".format(os.path.join(bindir, "python\n"))
    with open(os.path.join(bindir, "bad_shebang")) as f:
        assert f.read() == target
