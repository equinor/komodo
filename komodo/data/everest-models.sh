#!/bin/bash

set -e

while test $# -gt 0; do
    case "$1" in
        --prefix)
            shift
            export PREFIX=$1
            ;;
        --fakeroot)
            shift
            export FAKEROOT=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac

    shift
done

export TARGET=$FAKEROOT/$PREFIX/share/everest/models
mkdir -p $TARGET
rsync -av examples/egg $TARGET
