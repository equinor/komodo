#!/bin/bash

set -e

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

if [ -n "$REQ" ]; then
    pip install \
        --global-option build --global-option=--executable=$PYTHON \
        --root $FAKEROOT \
        --requirement $REQ --prefix $PREFIX
fi
python setup.py build --executable $PYTHON \
                install --prefix $PREFIX --root $FAKEROOT
