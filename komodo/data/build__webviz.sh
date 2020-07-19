#!/bin/bash

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
            export PREFIX_KOMODO=$1
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
set -e
make ARGS="--prefix=${PREFIX_KOMODO} --root=${FAKEROOT} --no-index --find-links cache" install
