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
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done


export CFLAGS="-ltinfo"
./configure --prefix=$PREFIX
make
make install
