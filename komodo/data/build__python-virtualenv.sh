#!/bin/bash

set -xe

while test $# -gt 0; do
    case "$1" in
        --fakeroot)
            shift
            export FAKEROOT=$1
            ;;
       --prefix)
            shift
            export PREFIX=$1
            ;;
        --virtualenv-interpreter)
            shift
            export VIRTUALENV_INTERPRETER=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done
$VIRTUALENV_INTERPRETER -m venv --copies --without-pip ${FAKEROOT}/${PREFIX} >&2
