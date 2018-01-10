#!/usr/bin/env python
from __future__ import print_function

from setuptools import setup

setup(
    name='Komodo',
    packages=['komodo'],
    package_dir={'komodo' : 'komodo'},
    scripts=['bin/kmd'],
    test_suite='tests',
)
