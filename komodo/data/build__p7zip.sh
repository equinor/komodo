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


cp -f makefile.linux_amd64_asm makefile.linux
make -j$JOBS all_test

DEST_BIN=$PREFIX/bin
DEST_SHARE=$PREFIX/lib/p7zip
DEST_SHARE_DOC=$PREFIX/share/doc/p7zip
DEST_MAN=$PREFIX/man
./install.sh $DEST_BIN $DEST_SHARE $DEST_MAN $DEST_SHARE_DOC

