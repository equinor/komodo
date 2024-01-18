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
        --virtualenv)
            shift
            export VIRTUALENV=$1
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
# $VIRTUALENV -p $VIRTUALENV_INTERPRETER -v --always-copy --never-download --no-setuptools --no-pip --no-wheel ${FAKEROOT}/${PREFIX} 1>&2
$VIRTUALENV_INTERPRETER -m venv --copies --without-pip ${FAKEROOT}/${PREFIX} >&2
