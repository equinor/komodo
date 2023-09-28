# This shell script is to be sourced in shells where any project in komodo is
# to be tested towards a built Komodo distribution, the prime example
# being komodo-releases/.github/workflows/run_tests_one_project.yml
# That file only depends on the bash function "run_tests()" being defined.
#
# The functions in here are provided as defaults, but are when needed
# overwritten in each projects' ci/testkomodo.sh if present.

run_tests () {
    copy_test_files

    install_test_dependencies

    pushd $CI_TEST_ROOT
    start_tests
    popd
}

install_test_dependencies () {
    if [ -f "test_requirements.txt" ]; then
        pip install -r test_requirements.txt
    else
        pip install pytest
    fi
}

copy_test_files () {
    if [ -d "$CI_SOURCE_ROOT/tests" ]; then
        cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT/tests
    fi
}

start_tests () {
    pytest
}

function ci_install_cmake {
    # Only used by older versions of ecl
    pip install cmake ninja

    local root=${KOMODO_ROOT}/${CI_KOMODO_RELEASE}/root

    export CMAKE_GENERATOR=Ninja
    export CMAKE_PREFIX_PATH=$root

    # Colour!
    export CFLAGS="${CFLAGS:-} -fdiagnostics-color=always"
    export CXXFLAGS="${CXXFLAGS:-} -fdiagnostics-color=always"
    export LDFLAGS="${LDFLAGS:-} -fdiagnostics-color=always"

    export LD_LIBRARY_PATH=$root/lib:$root/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
}

function ci_install_conan {
    # Only used by older versions of ecl
    pip install "conan<2"

    # Conan v1 bundles its own certs due to legacy reasons, so we point it
    # to the system's certs instead.
    export CONAN_CACERT_PATH=/etc/pki/tls/cert.pem
}

