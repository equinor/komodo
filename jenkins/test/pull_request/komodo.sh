#!/bin/bash
set -ex

function call_if_defined {
    set +e
    if $(declare -Ff "$1" > /dev/null); then
        "$1"
    fi
}

# Checkout and source pre-test script. This should set up site-local variables.
# For example, this script should enable RHEL devtoolset if applicable.
if [[ -n "${KOMODO_RELEASES_URL:-}" ]] && [[ -n "${KOMODO_TEST_SCRIPT:-}" ]]; then
    git clone "${KOMODO_RELEASES_URL}" komodo-releases

    pushd komodo-releases
    source "${KOMODO_TEST_SCRIPT}"
    popd
fi

# Source the komodo environment
source "${KOMODO_ROOT}/${RELEASE_NAME}/enable"

# Clone, checkout and source the project's correct version
git clone "${PROJECT_GIT_URL}" project --recursive
cd project

if [[ -n "${PROJECT_GIT_SHA1:-}" ]]; then
    # Checkout PR/specific commit
    git checkout "${PROJECT_GIT_SHA1}"
else
    # Checkout komodo's version
    extract_version=$(dirname "$0")/extract_version.py
    version=$("${extract_version}" "${KOMODO_ROOT}/${RELEASE_NAME}" "${PROJECT}")
    git checkout "${version}"
fi

source "${PROJECT_TEST_SCRIPT:-ci/jenkins/komodo.sh}"

if [ -n "${PROJECT_GIT_SHA1// }" ]; then
    call_if_defined pre_pull_request
else
    # No SHA1: not a PR build
    call_if_defined pre_komodo
fi

# This must be defined in "${PROJECT_TEST_SCRIPT}" that we have sourced
run_tests
