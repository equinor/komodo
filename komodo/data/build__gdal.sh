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
        --python)
            shift
            export PYTHON=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done
pushd gdal
./configure --prefix $PREFIX --without-libtool --with-odbc=no --with-pcre=no --with-hdf5=no --with-oci=no
make -j$JOBS
make install 
popd
