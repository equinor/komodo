def releaseDeployed(_PREFIX, _RELEASE_NAME) {
    sh """
        if [ -e $_PREFIX/$_RELEASE_NAME ]; then
            echo ${_RELEASE_NAME} is already deployed at ${_PREFIX}/${_RELEASE_NAME}!
            exit 1
        fi
    """
}

def configureGit(_GIT_EXEC) {
    sh """
        # fix error:
        # RPC failed; curl 56
        # SSL read: errno -5961
        # fatal: The remote end hung up unexpectedly
        # fatal: early EOF
        # fatal: index-pack failed
        ## start git config
        ## https://stackoverflow.com/questions/6842687
        $_GIT_EXEC config --global http.postBuffer 1048576000
        ## end
    """
}

def checkoutGitBranch(_GIT_EXEC, _GIT_REF) {
    sh """
        $_GIT_EXEC checkout $_GIT_REF
    """
}

def buildPythonEnv(_ENV_EXEC, _TARGET_ENV, _ENV_ARGS, _PIP_EXPRESSION) {
    sh """
        $_ENV_EXEC $_TARGET_ENV $_ENV_ARGS
        source $_TARGET_ENV/bin/activate
        python -m pip install --upgrade '$_PIP_EXPRESSION'
    """
}

def installKomodo(_PYTHON_ENV) {
    sh """
        source $_PYTHON_ENV
        pip install .
        rm -rf komodo
        rm -rf bin
        python -c "import komodo; print(komodo.__file__)"
    """
}

def cloneAndCheckoutKomodoConfig(_GIT_EXEC, _CONFIG_GIT_FORK, _CONFIG_GIT_REF, _TOKEN) {
    sh """
        $_GIT_EXEC clone https://${_TOKEN}@github.com/${_CONFIG_GIT_FORK}/komodo-releases.git
        pushd komodo-releases
        $_GIT_EXEC checkout $_CONFIG_GIT_REF
        popd
    """
}

def copyScripts(_KOMODO_ROOT, _KOMODO_RELEASES_ROOT) {
    // NOTE: This is to backwards compatible with the old komodo-releases setup
    // Should be removed as soon as we have moved all building to the komodo
    // instance
    sh """
        mkdir $_KOMODO_RELEASES_ROOT/src
        cp $_KOMODO_ROOT/setup-py.sh $_KOMODO_RELEASES_ROOT/src
        cp $_KOMODO_ROOT/enable.m4 $_KOMODO_RELEASES_ROOT
        cp $_KOMODO_ROOT/enable.in $_KOMODO_RELEASES_ROOT
        cp $_KOMODO_ROOT/enable.csh.in $_KOMODO_RELEASES_ROOT
    """
}

def validateRelease(_PYTHON_ENV, _KOMODO_RELEASES_ROOT, _PACKAGES, _REPOSITORY) {
    sh """
        source $_PYTHON_ENV
        pushd $_KOMODO_RELEASES_ROOT 

        # lint first
        python -m komodo.lint $_PACKAGES $_REPOSITORY

        # output maintainers
        python -m komodo.maintainer $_PACKAGES $_REPOSITORY

        popd
    """
}

def buildAndInstallRelease(_REPOSITORY, _RELEASE_FILE, _RELEASE_NAME, _KOMODO_RELEASES_ROOT, _PREFIX, _PIPELINE_STEPS, _DEVTOOLSET, _PYTHON_ENV, _CMAKE_EXECUTABLE, _GIT_EXEC, _PERMISSIONS_EXEC) {
    _PIP = sh(
        script: """
            source $_PYTHON_ENV
            which pip
        """,
        returnStdout: true
    ).trim()
    sh """
        source $_DEVTOOLSET
        source $_PYTHON_ENV
        set -xe

        pushd $_KOMODO_RELEASES_ROOT
        kmd $_RELEASE_FILE $_REPOSITORY                       \
            --jobs 6                                          \
            --release $_RELEASE_NAME                          \
            --tmp tmp                                         \
            --cache cache                                     \
            --prefix $_PREFIX                                 \
            --cmake $_CMAKE_EXECUTABLE                        \
            --pip $_PIP                                       \
            --git $_GIT_EXEC                                  \
            --postinst $_PERMISSIONS_EXEC                     \
            $_PIPELINE_STEPS                                  \

        popd
    """
}

def installLocalFiles(_KOMODO_RELEASES_ROOT, _PREFIX, _RELEASE_NAME, _PERMISSIONS_EXEC) {
    sh """
        pushd $_KOMODO_RELEASES_ROOT
        # Here we *very manually* copy the files local/local and local/local.csh to
        # the location of the main enable file. Dang - this is quite ugly ....
        if [ -e local/local ]; then
           cp local/local $_PREFIX/$_RELEASE_NAME/local
           $_PERMISSIONS_EXEC $_PREFIX/$_RELEASE_NAME/local
        fi

        if [ -e local/local.csh ]; then
           cp local/local.csh $_PREFIX/$_RELEASE_NAME/local.csh
           $_PERMISSIONS_EXEC $_PREFIX/$_RELEASE_NAME/local.csh
        fi
        popd
    """
}
