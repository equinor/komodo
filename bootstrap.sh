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

    if [ -f "runkmd.sh" ]; then
        echo "runkmd.sh exists, deleting"
        rm runkmd.sh
    fi
}

function install_komodo {
    # Install the environment that the kmd executable will run in. We also
    # install the virtualenv package because the user might specify to target
    # Python 2.7, where the 'venv' module doesn't exist.

    python3_bin=/usr/bin/python3

    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        # Travis provides Python via a virtualenv, lets respect that
        python3_bin=`which python`
    fi
    if [[ ! -f "${python3_bin}" ]]; then
        # Lets assume we're on an Equinor machine
        python3_bin=/prog/sdpsoft/python3.6.4/bin/python3
    fi
    if [[ ! -f "${python3_bin}" ]]; then
        echo "Couldn't find a Python 3 binary"
        exit 1
    fi

    echo "Installing Komodo"
    $python3_bin -m venv boot/kmd-env
    boot/kmd-env/bin/python -m pip install --upgrade pip pytest virtualenv
    boot/kmd-env/bin/python -m pip install .
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

function install_git {
    # git is too old for both RHEL6 and RHEL7, prefer the one from SDPSoft
    git_bin=/prog/sdpsoft/git-2.8.0/bin/git
    if [[ ! -f "${git_bin}" ]]; then
        echo "Couldn't find SDPSoft git, falling back to system git"
        git_bin=/usr/bin/git
    fi
    if [[ ! -f "${git_bin}" ]]; then
        echo "Couldn't find system git either, failing"
        exit 1
    fi

    echo "Using git"
    ln -s ${git_bin} boot/bintools/git
    boot/bintools/git --version
}

function install_build_env {
    echo "Using ${python_bin} for target"
    boot/kmd-env/bin/virtualenv --python=${python_bin} boot/build-env
    boot/build-env/bin/pip install --upgrade pip setuptools wheel virtualenv
    ln -s $PWD/boot/build-env/bin/pip boot/bintools/
}

function create_runkmd {
    cat << EOF > runkmd.sh
#!/bin/bash
export PATH=$PWD/boot/bintools:$PWD/boot/build-env/bin:\$PATH
$PWD/boot/kmd-env/bin/kmd "\$@"
EOF
    chmod +x runkmd.sh
}

cleanup
mkdir -p boot/bintools
install_komodo
install_build_env
install_devtoolset
install_cmake
install_git
create_runkmd
