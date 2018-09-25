#!/usr/bin/env python
import time
import unittest
import contextlib
import shutil
import tempfile
import subprocess
import os

import komodo

@contextlib.contextmanager
def tmp():
    cwd0 = os.getcwd()
    dname = tempfile.NamedTemporaryFile().name
    os.mkdir(dname)
    os.chdir(dname)

    yield dname

    os.chdir(cwd0)
    shutil.rmtree(dname)


@contextlib.contextmanager
def pushd(path):
    cwd0 = os.getcwd()
    if not os.path.isdir(path):
        os.mkdir(path)
    os.chdir(path)

    yield

    os.chdir(cwd0)




def populate_dir():
    rel_list = ["stable", "testing", "bleeding"]
    ts_list = [1, 2, 3, 4, 5]
    for ts in ts_list:
        for rel in rel_list:
            rel_path = '{}-{}'.format(rel, ts)
            os.mkdir(rel_path)

    os.mkdir("just-a-directory")


def check_dir(root, expected, does_not_exist):
    for link,target in expected:
        assert(os.path.islink(link))
        assert(os.path.isdir(target))
        assert(target == os.readlink(link))

    for path in does_not_exist:
        assert(not os.path.exists(path))


class TestLink(unittest.TestCase):

    def test_link(self):
        with tmp() as dname:
            populate_dir()
            with pushd("somewhere_else"):
                komodo.update_links(dname)

            check_dir("./", [("stable", "stable-5"),
                             ("testing", "testing-5"),
                             ("bleeding", "bleeding-5")],
                      ["stable-1", "testing-3", "bleeding-2"])

            self.assertTrue(os.path.isdir("just-a-directory"))


    def test_kmd_link(self):
        with tmp() as dname:
            populate_dir()
            with pushd("somehwere_else"):
                kmd_link = os.path.join( os.path.dirname( __file__), "../bin/kmd_link")
                subprocess.check_call([kmd_link, dname])

            check_dir("./", [("stable", "stable-5"),
                             ("testing", "testing-5"),
                             ("bleeding", "bleeding-5")],
                      ["stable-1", "testing-3", "bleeding-2"])

            self.assertTrue(os.path.isdir("just-a-directory"))




    def test_link_name_exists(self):
        with tmp():
            os.mkdir("stable")
            os.mkdir("stable-10")

            with self.assertRaises(IOError):
                komodo.update_links("./")


if __name__ == '__main__':
    unittest.main()
