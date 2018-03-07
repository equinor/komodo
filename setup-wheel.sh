#!/bin/bash

set -e

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
        *)
            export OPTS="$OPTS $1"
            ;;
    esac

    shift
done

python setup.py build --executable $PREFIX/bin/python \
                install --prefix $PREFIX --root $FAKEROOT
