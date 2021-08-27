import java.util.regex.Pattern

def getPython() {
    if(params.RH_VERSION == "6") {
        if (params.PYTHON_VERSION == "2.7") {
            return "/prog/sdpsoft/python2.7.14/bin/python"
        } else {
            return "/prog/sdpsoft/python3.6.4/bin/python3"
        }
    } else if (params.RH_VERSION == "7") {
        if (params.PYTHON_VERSION == "3.8") {
            return "/opt/rh/rh-python38/root/bin/python3.8"
        } else {
            return "/usr/bin/python${params.PYTHON_VERSION}"
        }
    }
    throw new Exception("Bad RH version " + params.RH_VERSION)
}

def getAgentLabel() {
    params.RH_VERSION == "6" ? "komodo-deploy" : "komodo-deploy7"
}

def getReleaseName() {
    if (params.PYTHON_VERSION == "2.7") {
        return "${params.MATRIX_FILE_BASE}-py27-rhel${params.RH_VERSION}"
    } else if (params.PYTHON_VERSION == "3.6") {
        return "${params.MATRIX_FILE_BASE}-py36-rhel${params.RH_VERSION}"
    } else if (params.PYTHON_VERSION == "3.8") {
        return "${params.MATRIX_FILE_BASE}-py38-rhel${params.RH_VERSION}"
    }
    throw new Exception("Bad Python version '${params.PYTHON_VERSION}'")
}

def gitClone(String url, String branchName) {
    @NonCPS
    def getTargetDir = { ->
        def pattern = Pattern.compile("/([^./]+)(?:.git)?\\z")
        def matcher = pattern.matcher(url)
        if (!matcher.find()) {
            throw Exception("Could not extract the repository name from URL: ${url}")
        }
        matcher.group(1)
    }

    checkout([
        $class: 'GitSCM',
        branches: [[name: branchName]],
        doGenerateSubmoduleConfigurations: false,
        extensions: [
            [$class: 'RelativeTargetDirectory', relativeTargetDir: getTargetDir()],
            [$class: 'CloneOption', shallow: true, noTags: true],
        ],
        submoduleCfg: [],
        userRemoteConfigs: [[
            // ertomatic's ID
            credentialsId: '5cf748b8-c6d0-4014-8a72-5726b185a7c7',
            url: url
        ]]
    ])
}

def call(Map args = [:]) {
    pipeline {
        agent { label getAgentLabel() }

        parameters {
            string name: 'RH_VERSION', defaultValue: '6',
                description: 'Dictates on what Red Hat version the build runs, as well as what version it targets'
            string name: 'PYTHON_VERSION', defaultValue: '2.7',
                description: 'The target Python version'

            string name: 'MATRIX_FILE_BASE', defaultValue: 'bleeding',
                description: 'The matrix file that is to be built. I.e. bleeding or 2020.06.05. It is expected that there is a matrix file in komodo-release/releases/matrices/{base}.yml.'

            string name: 'PREFIX', defaultValue: '/prog/res/komodo',
                description: 'The install prefix.'

            booleanParam name: 'deploy', defaultValue: true,
                description: 'Whether or not to deploy'
            booleanParam name: 'overwrite', defaultValue: false,
                description: 'Whether or not to overwrite if build already exist'

            string name: 'CODE_GIT_FORK', defaultValue: 'equinor',
                description: 'The fork to the get the komodo build system from'
            string name: 'CODE_GIT_REF', defaultValue: 'master',
                description: ' The branch to get the komodo build system from'
            string name: 'CONFIG_GIT_FORK', defaultValue: 'equinor',
                description: 'The fork to get the the komodo releases from'
            string name: 'CONFIG_GIT_REF', defaultValue: 'master',
                description: 'The branch to get the komodo releases from'
        }

        environment {
            MATRIX_FILE = "releases/matrices/${params.MATRIX_FILE_BASE}.yml"
        }

        stages {
            stage('Already deployed') {
                when {
                    expression {
                        !params.overwrite
                    }
                }
                steps {
                    script {
                        if (fileExists("${params.PREFIX}/${getReleaseName()}")) {
                            error "${getReleaseName()} is already deployed at ${params.PREFIX}/${getReleaseName()}!"
                        }
                    }
                }
            }
            stage('Build') {
                steps {
                    script {
                        if (params.MATRIX_FILE_BASE == '')
                            error 'MATRIX_FILE_BASE not set'
                        if (params.RH_VERSION == '')
                            error 'RH_VERSION not set'
                        if (params.PYTHON_VERSION == '')
                            error 'PYTHON_VERSION not set'
                    }

                    dir(getReleaseName()) {
                        script {
                            if (fileExists("."))
                                error "Build ${getReleaseName()} is already in progress."
                        }

                        gitClone "https://github.com/${params.CODE_GIT_FORK}/komodo.git",
                            params.CODE_GIT_REF
                        gitClone "https://github.com/${params.CONFIG_GIT_FORK}/komodo-releases.git",
                            params.CONFIG_GIT_REF

                        script {
                            def komodoPath = "${env.WORKSPACE}/${getReleaseName()}/komodo"
                            def configPath = "${env.WORKSPACE}/${getReleaseName()}/komodo-releases"
                            def releaseFile = "${getReleaseName()}.yml"
                            def matrixFile = "${configPath}/releases/matrices/${params.MATRIX_FILE_BASE}.yml"

                            // Bootstrap
                            sh "cd ${komodoPath}; ./bootstrap.sh ${getPython()}"

                            // Transpile
                            sh "cd ${configPath}; ${komodoPath}/boot/kmd-env/bin/komodo-transpiler transpile --matrix-file=${matrixFile} --output releases"

                            // Lint
                            sh "cd ${configPath}; ${komodoPath}/boot/kmd-env/bin/komodo-lint releases/${releaseFile} repository.yml"

                            // Run!
                            withEnv(["TMPDIR=${configPath}/tmp"]) {
                                sh """
                            cd ${configPath}
                            ${komodoPath}/runkmd.sh                                    \
                                releases/${releaseFile}                                \
                                repository.yml                                         \
                                --download                                             \
                                --build                                                \
                                ${params.deploy ? '--install' : '--dry-run'}           \
                                --jobs 6                                               \
                                --release ${getReleaseName()}                          \
                                --tmp tmp                                              \
                                --cache cache                                          \
                                --prefix ${params.PREFIX}                              \
                                --pip ${komodoPath}/boot/build-env/bin/pip             \
                                --virtualenv ${komodoPath}/boot/kmd-env/bin/virtualenv \
                                --locations-config locations.yml
                            """
                            }
                        }
                    }
                }
            }
        }
        post {
            cleanup {
                cleanWs()
            }
        }
    }
}
