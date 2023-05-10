#!/usr/bin/env python
import sys
from ctypes import CDLL, c_char_p

lib = CDLL("libkmd.so")
foo = lib.foo
foo.restype = c_char_p
foo.argtypes = ()

# Test that libkmd.so is loaded correctly
val = foo()
if val != b"bar":
    sys.stderr.write(f"foo() returned '{val}' instead of 'bar'\n")
    sys.exit(1)
