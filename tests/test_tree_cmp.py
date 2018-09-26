#!/usr/bin/env python
from __future__ import print_function
import os
import contextlib
import tempfile
import unittest
import shutil

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


class TreeTest(unittest.TestCase):

    def test_tree(self):
        with tmp():
            os.makedirs("prefix1/stable/root/bin")
            os.makedirs("prefix2/stable/root/bin")

            with open("prefix1/stable/root/bin/file", "w") as f:
                f.write("Hello")


            self.assertFalse( komodo.tree_equal("prefix1/stable", "prefix2/stable"))

            with open("prefix2/stable/root/bin/file", "w") as f:
                f.write("Hello")

            self.assertTrue(komodo.tree_equal("prefix1/stable", "prefix2/stable"))
            os.makedirs("prefix1/stable/root/lib")
            self.assertFalse( komodo.tree_equal("prefix1/stable", "prefix2/stable"))

if __name__ == '__main__':
    unittest.main()
