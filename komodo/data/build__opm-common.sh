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
            ;;
        --pythonpath)
            shift
            export PYTHONPATH=$1
            ;;
        --pip)
            shift
            export PIP=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

root=$FAKEROOT/$PREFIX
incdir=$root/include:$PWD
libdir=$root/lib:$root/lib64

cd python

# Patch: put the extension inside the 'opm' module
sed -i "s/'libopmcommon_python'/'opm.libopmcommon_python'/" setup.py
python setup.py build_ext     \
       --library-dirs=$libdir \
       --include-dirs=$incdir 1>&2
python setup.py bdist_wheel 1>&2

$PIP install dist/*   \
    --root $FAKEROOT \
    --no-deps        \
    --prefix $PREFIX 1>&2
