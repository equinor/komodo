function ci_install_cmake {
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
