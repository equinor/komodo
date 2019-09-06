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
        --target)
            shift
            export TARGET=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

set -x

./configure --prefix=$PREFIX            \
            --enable-shared             \
            --enable-optimizations      \
            --with-ensurepip=upgrade    \
            $OPTS

make -j$JOBS
make -j$JOBS altinstall

ln -s $PREFIX/bin/python3 $PREFIX/bin/python

# get a fresh pip as a part of the installation
$PREFIX/bin/pip install \
    --upgrade --ignore-installed --force-reinstall --prefix $PREFIX \
    pip

# this is a mega hack
# the problem arises because of a subtle detail in distutils and sysconfig.
#
# distutils detects that the python that tries to it is in a python source
# tree, in which case it assumes that it wants to hard-link all scripts with a
# shebang (#!) to this particular interpreter.
#
# This isn't ideal since we want the install to be relocatable (in fact, we
# know for sure that we *will* relocate it).
#
# Additionally, the sysconfig module, which is queried when building non-pure
# modules against this particular python wants to grab python's build flags
# etc, records the paths from the build configuration. These won't match up to
# the target paths of komodo, so sed to replace them all with the actual target
# install path.

#if [ -n ${TARGET+x} ]; then
#    find $PREFIX -type f -exec grep -Iq . {} \; -and \
#        -exec sed --in-place --follow-symlinks s,$PREFIX,$TARGET, {} \;
#fi
