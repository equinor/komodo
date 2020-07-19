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
        --requirement)
            shift
            export REQ=$1
            ;;
        --pip)
            shift
            export PIP=$1
            ;;
        --pythonpath)
            shift
            export PYTHONPATH=$1
            ;;
        --ld-library-path)
            shift
            export LD_LIBRARY_PATH=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac

    shift
done

PYTHONEXECUTABLE=$FAKEROOT/$PREFIX/bin/python

$PIP install . \
    --global-option build --global-option=--executable=$PYTHONEXECUTABLE \
    --ignore-installed                                                   \
    --root $FAKEROOT                                                     \
    --no-deps                                                            \
    --prefix $PREFIX 1>&2
