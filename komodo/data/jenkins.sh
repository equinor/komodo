#!/bin/bash

export SHELL=/bin/bash
source /opt/rh/devtoolset-3/enable
set -xe

/prog/sdpsoft/git-2.8.0/bin/git checkout $GIT_REF

/prog/sdpsoft/git-2.8.0/bin/git clone https://github.com/equinor/komodo.git src

pushd src
export PYTHONPATH=$PYTHONPATH:$PWD
popd


# temporary hack since enable scripts have been moved into src and src/komodo.py
# works relative to working directory
cp -v src/enable* .


export http_proxy=http://www-proxy.statoil.no:80
export HTTP_PROXY=http://www-proxy.statoil.no:80
export https_proxy=http://www-proxy.statoil.no:80
export HTTPS_PROXY=http://www-proxy.statoil.no:80

export PIP_CERT=/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt


export CMAKE_EXECUTABLE=/usr/bin/cmake3
PACKAGES=releases/$RELEASE.yml

# lint first
$BUILDPY/bin/python src/komodo/lint.py $PACKAGES repository.yml

# run komodo!
$BUILDPY/bin/python -u src/bin/kmd $PACKAGES repository.yml  \
    --jobs 4                                               \
    --release $RELEASE                                     \
    --tmp tmp                                              \
    --cache cache                                          \
    --prefix $PREFIX                                       \
    --cmake $CMAKE_EXECUTABLE                              \
    --pip $BUILDPY/bin/pip                                 \
    --git  /prog/sdpsoft/git-2.8.0/bin/git                 \
    --postinst /project/res/bin/res_perm                   \
    $PIPELINE_STEPS                                        \
