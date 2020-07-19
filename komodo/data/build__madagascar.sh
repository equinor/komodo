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
        --MATLAB)
            shift
            export MATLAB=$1
            ;;
        --MEX)
            shift
            export MEX=$1
            ;;
        --API)
            shift
            export MEX=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

pushd user

git clone git@git.equinor.com:MRAVA/madagascar_mrava.git
popd

export DESTDIR=$FAKEROOT

./configure --prefix=$PREFIX API=$API MATLAB=$MATLAB MEX=$MEX
make -j$JOBS
make install
