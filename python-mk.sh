#!/bin/bash

set -e

JOBS=1

while test $# -gt 0; do
    case "$1" in
        --cmake)
            shift
            export CMAKE_EXEC=$1
            ;;
        --fakeroot)
            shift
            ;;
        --jobs)
            shift
            export JOBS=$1
            ;;
        --prefix)
            shift
            export PREFIX=$1
            ;;
        --python)
            shift
            ;;
        --target)
            shift
            export TARGET=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

set -x

./configure --prefix=$PREFIX                    \
            --enable-shared                     \
            --enable-optimizations              \
            --with-ensurepip=install            \
            "LDFLAGS=-Wl,-rpath=$PREFIX/lib"    \
            $OPTS

make -j$JOBS
make -j$JOBS install
