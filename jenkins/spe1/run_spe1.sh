#!/bin/bash
set -e
set -x

function on_exit {
    mkdir $WORKSPACE/archive
    cp -R $TEST_ROOT/spe1_out $WORKSPACE/archive/
    rm -rf $TEST_ROOT
}

trap on_exit EXIT

TEST_ROOT=$(mktemp -d)/test

source ${PREREQ}
source ${KOMODO_ROOT}/${RELEASE}/enable

mkdir $TEST_ROOT

cp -R jenkins/spe1/* $TEST_ROOT

pushd $TEST_ROOT

git clone https://github.com/OPM/opm-data.git

echo "Initiating Ert run for Spe1..."

ert ensemble_experiment spe1.ert

echo "Finished"

popd
