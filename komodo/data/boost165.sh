#!/bin/bash

set -e

JOBS=1

while test $# -gt 0; do
    case "$1" in
        --cmake)
            shift
            export CMAKE_EXEC=$1
            ;;
        --jobs)
            shift
            export JOBS=$1
            ;;
        --src)
            shift
            export SRCDIR=$1
            ;;
        --prefix)
            shift
            export PREFIX=$1
            ;;
        --python)
            shift
            export PYTHON=$1
            ;;
        --fakeroot)
            shift
            export FAKEROOT=$1
            ;;
        --ld-library-path)
            shift
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

./bootstrap.sh --prefix=$PREFIX           \
               --libdir=$PREFIX/lib64     \
               --with-python=$PYTHON      \
               $OPTS

./b2 -j $JOBS cxxflags="-std=c++11" install
