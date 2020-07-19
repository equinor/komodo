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
        --path)
            shift
            export PATH=$1
            ;;
        --pythonpath|--virtualenv|--pip|--ld-library-path)
            shift
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

python configure.py \
    --confirm-license \
    --disable=QtNfc \
    --disable=QtAndroidExtras \
    --disable=QtBluetooth \
    --disable=QtPositioning \
    --disable=QtSensors \
    --disable=QtSerialPort \
    --disable=Enginio \
    --qmake=$FAKEROOT$PREFIX/bin/qmake \
    --no-dist-info \
    $OPTS
make -j$JOBS
make -j$JOBS install
