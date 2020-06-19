#!/bin/bash -eu

prefix=$1

# Compile
echo 'char*foo(){return"bar";}' > /tmp/lib.c
cc -shared -o/tmp/libkmd.so -fPIC /tmp/lib.c

# Copy into komodo release
cp /tmp/libkmd.so "${prefix}/root/lib"
