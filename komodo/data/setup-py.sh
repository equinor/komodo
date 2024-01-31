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
            ;;
        --path)
            shift
            export PATH=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac

    shift
done

unset DESTDIR
$PIP install $OPTS .           \
    --ignore-installed   \
    --root $FAKEROOT     \
    --no-deps            \
    --no-cache-dir       \
    --prefix $PREFIX 1>&2
