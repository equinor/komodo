function ci_install_cmake {
    pip install --upgrade pip
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
    pip install conan

    # Conan v1 bundles its own certs due to legacy reasons, so we point it
    # to the system's certs instead.
    export CONAN_CACERT_PATH=/etc/pki/tls/cert.pem
}

copy_test_files () {
    if [ -d "$CI_SOURCE_ROOT/tests" ]; then
        cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT/tests
    fi
    if [ -d "$CI_SOURCE_ROOT/test-data" ]; then
        cp -r $CI_SOURCE_ROOT/test-data $CI_TEST_ROOT/test-data
    fi
}

install_package () {
    pip install .
}

install_test_dependencies () {
    if [ -f "test_requirements.txt" ]; then
        pip install -r test_requirements.txt
    else
        pip install pytest
    fi
}

start_tests () {
    pytest
}

run_tests_default () {
    copy_test_files

    if [ ! -z "${CI_PR_RUN:-}" ]
    then
        install_package
    fi

    install_test_dependencies

    pushd $CI_TEST_ROOT
    start_tests
}

function run_tests {
    run_tests_default
}
