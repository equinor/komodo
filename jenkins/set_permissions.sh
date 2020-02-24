#!/bin/bash

if [ -z "$1" ]; then
    echo "Missing required positional argument FILE"
    exit 1
fi

find $1 -type f -exec chmod o+r {} \;
find $1 -type f -executable -exec chmod o+rx {} \;
find $1 -type d -exec chmod o+xr {} \;
