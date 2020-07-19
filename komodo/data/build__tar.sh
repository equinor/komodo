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

find . -maxdepth 1 -mindepth 1 -type d -exec rsync -a {} $FAKEROOT/$PREFIX \;
