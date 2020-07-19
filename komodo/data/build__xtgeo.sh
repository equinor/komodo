#!/bin/bash

set -xe

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
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

rm -fr swigbuild
mkdir -p swigbuild

rm -fr swig
mkdir -p swig

INST=$(pwd)
pushd swigbuild

wget https://sourceforge.net/projects/swig/files/swig/swig-4.0.1/swig-4.0.1.tar.gz
tar xf swig-4.0.1.tar.gz
pushd swig-4.0.1
wget "https://ftp.pcre.org/pub/pcre/pcre-8.38.tar.gz"

echo "Running configure..."
./configure --prefix="$INST/swig"

echo "Running make..."
make
echo "Running make install..."

export DESTDIR=/
make install

popd
popd

export PATH=$PATH:$INST/swig/bin
swig -swiglib


PYTHONEXECUTABLE=$PREFIX/bin/python
export SWIG_INSTALL_KOMODO=1  # message to setup.py in xtgeo

python setup.py build --executable $PYTHONEXECUTABLE \
       install --prefix $PREFIX --root $FAKEROOT \
       --cmake-executable $CMAKE_EXEC \
       --generator "Unix Makefiles"

# Just look if stuff is installed
for f in $(find $FAKEROOT/$PREFIX -name "xtgeo*"); do
    printf "XTGEO: $f\n\n"
done
