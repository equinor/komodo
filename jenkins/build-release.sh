#!/bin/bash

export SHELL=/bin/bash
source $DEVTOOLSET
set -e


# fix error:
# RPC failed; curl 56
# SSL read: errno -5961
# fatal: The remote end hung up unexpectedly
# fatal: early EOF
# fatal: index-pack failed
## start git config
## https://stackoverflow.com/questions/6842687
$GIT_EXEC config --global http.postBuffer 1048576000
## end


$GIT_EXEC checkout $CONFIG_GIT_REF

$GIT_EXEC clone https://github.com/${CODE_GIT_FORK}/komodo.git src

pushd src
$GIT_EXEC checkout $CODE_GIT_REF
export PYTHONPATH=$PYTHONPATH:$PWD
popd

# temporary hack since enable scripts have been moved into src and src/komodo.py
# works relative to working directory
cp -v src/enable* .

export http_proxy=$PROXY
export HTTP_PROXY=$PROXY
export https_proxy=$PROXY
export HTTPS_PROXY=$PROXY

PACKAGES=releases/$RELEASE.yml

# lint first
$BUILDPY/bin/python -m komodo.lint $PACKAGES repository.yml

# output maintainers
$BUILDPY/bin/python -m komodo.maintainer $PACKAGES repository.yml

if [[ $dryrun == "true" ]]; then
   PIPELINE_STEPS="--dry-run $PIPELINE_STEPS"
fi

if [[ $inplace == "true" ]]; then
   PIPELINE_STEPS="--inplace-deploy $PIPELINE_STEPS"
fi

set -xe

# run komodo!
$BUILDPY/bin/python -u src/bin/kmd $PACKAGES repository.yml  \
    --jobs 6                                               \
    --release $RELEASE                                     \
    --tmp tmp                                              \
    --cache cache                                          \
    --prefix $PREFIX                                       \
    --cmake $CMAKE_EXECUTABLE                              \
    --pip $BUILDPY/bin/pip                                 \
    --git  $GIT_EXEC                                       \
    --postinst $PERMISSIONS_EXEC                           \
    $PIPELINE_STEPS                                        \



# Here we *very manually* copy the files local/local and local/local.csh to
# the location of the main enable file. Dang - this is quite ugly ....
if [ -e local/local ]; then 
   cp local/local $PREFIX/$RELEASE/local
   $PERMISSIONS_EXEC $PREFIX/$RELEASE/local
fi	


if [ -e local/local.csh ]; then 
   cp local/local.csh $PREFIX/$RELEASE/local.csh
   $PERMISSIONS_EXEC $PREFIX/$RELEASE/local.csh
fi
