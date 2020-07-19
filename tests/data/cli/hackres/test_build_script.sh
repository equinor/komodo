#!/bin/sh
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
    esac
    shift
done

FAKEPREFIX=${FAKEROOT}/${PREFIX}
mkdir -p "${FAKEPREFIX}/lib/"
touch "${FAKEPREFIX}/lib/hackres.so"
