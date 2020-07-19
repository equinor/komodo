#!/bin/bash

set -ex

while test $# -gt 0; do
    case "$1" in
        --cmake)
            shift
            export CMAKE_EXEC=$1
            ;;
        --fakeroot)
            shift
            export FAKEROOT=$1
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
        --pip|--virtualenv|--virtualenv-interpreter|--ld-library-path)
            shift
            ;;
        --pythonpath)
            shift
            export PYTHONPATH=$1
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

python configure.py \
    --sip-module PyQt5.sip \
    $OPTS
make -j$JOBS
DESTDIR= make install -j$JOBS
