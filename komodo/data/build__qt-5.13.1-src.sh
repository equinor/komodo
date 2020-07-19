#!/bin/bash

set -ex

export JOBS=1

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

# From https://download.qt.io/archive/qt/5.13/5.13.1/single/md5sums.txt
# Checks the integrity of the downloaded tarball by comparing the md5sum
# obtained from QT's website, with the one from the tarball itself.
echo "d66b1da335d0c25325fdf493e9044c38  ../qt5-5.13.1.tar.xz" |md5sum -c

# As per https://wiki.qt.io/Building_Qt_5_from_Git we avoid shadow build inside the source tree
cd ..
mkdir build
cd build

export INSTALL_ROOT=$FAKEROOT

../qt5-5.13.1/configure -prefix $PREFIX -datadir $PREFIX/share -I /project/res/komodo/repository/xkbcommon/root/include -L /project/res/komodo/repository/xkbcommon/root/lib64 $OPTS

make -j$JOBS 
make -j$JOBS install
