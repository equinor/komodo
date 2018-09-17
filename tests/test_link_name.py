#!/usr/bin/env python
from __future__ import print_function
import time
import unittest

import komodo

class TestReleaseName(unittest.TestCase):

    def test_name(self):
        release_name = komodo.make_release_name("release")
        name, seconds = komodo.split_release_name(release_name)

        self.assertEqual(name, "release")
        self.assertTrue( isinstance(seconds, int))

        name, seconds = komodo.split_release_name("release-with-dash-100")
        self.assertEqual(name, "release-with-dash")
        self.assertEqual(seconds,100)

        rel1 = komodo.make_release_name("stable")
        time.sleep(2)
        rel2 = komodo.make_release_name("stable")

        _, t1 = komodo.split_release_name(rel1)
        _, t2 = komodo.split_release_name(rel2)

        self.assertGreater(t2,t1)


if __name__ == '__main__':
    unittest.main()
