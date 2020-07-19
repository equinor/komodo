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
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

export DESTDIR=$FAKEROOT

# xkbcommon uses meson/ninja for building, which we will pip install
/prog/sdpsoft/python3.6.4/bin/virtualenv -p /prog/sdpsoft/python3.6.4/bin/python3 venv
source venv/bin/activate
pip3 install meson ninja

meson setup --prefix=${PREFIX} $OPTS build
ninja -C build
cd build
ninja install

# allow shebang fixup script to complete by making an empty bin folder
mkdir -p ${FAKEROOT}${PREFIX}/bin
