#!/bin/bash
set -eux

function usage {
    echo "Usage: $0 [TARGET PYTHON EXECUTABLE]"
    exit 1
}

[ -z "${1:-}" ] && usage
[[ ! -f "$1" ]] && usage

python_bin=$1

function cleanup {
    if [ -d "boot" ]; then
        echo "boot/ exists, deleting"
        rm -r boot
    fi

    if [ -f "run_kmd.sh" ]; then
        echo "run_kmd.sh exists, deleting"
        rm run_kmd.sh
    fi
}

function install_komodo {
    # Install the environment that the kmd executable will run in.
    echo "Installing Komodo"
    $python_bin -m venv boot/kmd-env
    boot/kmd-env/bin/python -m pip install -U pip
    boot/kmd-env/bin/python -m pip install "urllib3<2" virtualenv pytest .
}

function install_devtoolset {
    # Install devtoolset simply by symlinking everything from its bin. Note that
    # we don't need to use LD_LIBRARY_PATH or any other environment variables to
    # get this to work.

    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        # Github Actions uses Ubuntu which doesn't have devtoolset, but the build tools
        # are new enough
        return
    fi
    if [[ ! -d "/opt/rh/devtoolset-8" ]]; then
        echo "Couldn't find Devtoolset 8"
        exit 1
    fi

    echo "Using devtoolset-8"
    for binfile in /opt/rh/devtoolset-8/root/usr/bin/*; do
        ln -s $binfile boot/bintools/
    done
    boot/bintools/gcc --version
}

function install_cmake {
    # The RHEL /usr/bin/cmake is CMake 2.8, which is positively ancient,
    # Use /usr/bin/cmake3 instead.

    cmake_bin=/usr/bin/cmake3
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        # On Ubuntu 18.04 (bionic), the 'cmake' package is CMake 3.10
        cmake_bin=/usr/local/bin/cmake
    fi
    if [[ ! -f "${cmake_bin}" ]]; then
        echo "Couldn't find a CMake3 executable"
        exit 1
    fi

    echo "Using CMake3"
    ln -s ${cmake_bin} boot/bintools/cmake
    boot/bintools/cmake --version
}

function install_build_env {
    echo "Using ${python_bin} for target"
    boot/kmd-env/bin/virtualenv --python=${python_bin} boot/build-env
    boot/build-env/bin/pip install --upgrade pip setuptools wheel virtualenv
    ln -s $PWD/boot/build-env/bin/pip boot/bintools/
}

function create_run_kmd {
    cat << EOF > run_kmd.sh
#!/bin/bash
export PATH=$PWD/boot/bintools:$PWD/boot/build-env/bin:\$PATH
export VIRTUAL_ENV=$PWD/boot/build-env
$PWD/boot/kmd-env/bin/kmd "\$@"
EOF
    chmod +x run_kmd.sh
}

cleanup
mkdir -p boot/bintools
install_komodo
install_build_env
install_devtoolset
install_cmake
create_run_kmd
