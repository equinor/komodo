@Grab('org.yaml:snakeyaml:1.26')

import java.nio.file.Paths
import org.yaml.snakeyaml.Yaml

def getVersion(project) {
    def path = sh(
        script: """/usr/bin/python -c 'import os;print(os.path.realpath("/prog/res/komodo/${env.KOMODO_RELEASE}"))'""",
        returnStdout: true
    ).trim()

    @NonCPS
    def getYamlPath = { ->
        def relPath = Paths.get(path)
        def yamlPath = relPath.resolve(relPath.getFileName())
        yamlPath.toString()
    }

    @NonCPS
    def parseVersion = { file ->
        def yaml = new Yaml()
        def pkgs = yaml.load(file)
        def ver = pkgs[project].version
        def index = ver.indexOf('+')
        index == -1 ? ver : ver[0..<index]
    }

    parseVersion readFile(getYamlPath())
}

def call(Map args = [:]) {
    def project = args.project
    def pkg = args.pkg
    def isPullRequest = args.pullRequest
    def gitCredentialsID = args.gitCredentialsID
    def agentLabel = params.KOMODO_RELEASE.contains("rhel7") ? "scout-ci7" : "scout-ci"

    pipeline {
        agent { label agentLabel }

        parameters {
            string name: 'GIT_CODE_FORK', defaultValue: 'Equinor'
            string name: 'GIT_CODE_REF', defaultValue: 'master'

            string name: 'GIT_HELPER_FORK', defaultValue: 'Equinor'
            string name: 'GIT_HELPER_REF', defaultValue: 'master'

            string name: 'KOMODO_RELEASE', defaultValue: 'bleeding-py36'
        }

        options {
            ansiColor('xterm')
        }

        environment {
            KOMODO_ROOT        = "/prog/res/komodo"

            KOMODO             = 1
            CI_KOMODO          = 1

            CI_PR_RUN          = "${isPullRequest == true ? "1" : ""}"
            CI_SOURCE_ROOT     = "${env.WORKSPACE}/source-root"
            CI_TEST_ROOT       = "${env.WORKSPACE}/test-root"
            CI_KOMODO_RELEASE  = "${params.KOMODO_RELEASE}"

            EQUINOR_TESTDATA_ROOT = "/project/res-testdata/ErtTestData/fmu-test-data"
        }

        stages {
            stage('Pre-setup') {
                steps {
                    deleteDir()

                    // Install komodoenv
                    sh '/prog/sdpsoft/python3.6.4/bin/python3 -m venv komodoenv-venv'
                    sh 'komodoenv-venv/bin/pip install --upgrade pip setuptools wheel'
                    sh 'komodoenv-venv/bin/pip install git+https://github.com/equinor/komodoenv.git'

                    // Use komodoenv to generate a komodoenv
                    sh "komodoenv-venv/bin/komodoenv -r${env.CI_KOMODO_RELEASE} test-kenv"

                    // Git clone
                    script {
                        if (isPullRequest == true){
                            checkout([$class: 'GitSCM',
                                    branches: [[name: "remotes/origin/pr/${ghprbPullId}/head"]],
                                    extensions: [
                                    [$class: 'RelativeTargetDirectory', relativeTargetDir: 'source-root'],
                                ],
                                    userRemoteConfigs: [[
                                    url: "https://github.com/${params.GIT_CODE_FORK}/${project}",
                                    refspec: "+refs/pull/${ghprbPullId}/*:refs/remotes/origin/pr/${ghprbPullId}/*",
                                    credentialsId: "${gitCredentialsID}"  // ertomatic
                                ]],
                            ])
                        }
                        else {
                            checkout([$class: 'GitSCM',
                                    branches: [[name: getVersion(pkg)]],
                                    extensions: [
                                    [$class: 'RelativeTargetDirectory', relativeTargetDir: 'source-root'],
                                ],
                                    userRemoteConfigs: [[
                                    url: "https://github.com/${params.GIT_CODE_FORK}/${project}",
                                    credentialsId: "${gitCredentialsID}"  // ertomatic
                                ]],
                            ])
                        }
                    }

                    sh "mkdir -p ${env.CI_TEST_ROOT}"
                }
            }

            stage('Run Tests') {
                steps {
                    sh "wget https://raw.githubusercontent.com/${params.GIT_HELPER_FORK}/komodo/${params.GIT_HELPER_REF}/jenkins/ci_helper.sh"

                    dir(env.CI_SOURCE_ROOT) {

                        sh """\
                        set +x
                        source ${env.WORKSPACE}/test-kenv/enable
                        source /opt/rh/devtoolset-8/enable

                        # Additional CI environment variables
                        export CI_PYTHON_VERSION=\$(python -c 'import sys;print("%s.%s"%sys.version_info[:2])')

                        # Setup colour
                        export CLICOLOR=1
                        export CLICOLOR_FORCE=1
                        export PYTEST_ADDOPTS="--color=yes"

                        GIT_VERSION=2.8.0
                        source /prog/sdpsoft/env.sh

                        source ${env.WORKSPACE}/ci_helper.sh

                        set -x
                        git log -n 1
                        source ${env.CI_SOURCE_ROOT}/ci/jenkins/testkomodo.sh
                        git log -n 1
                        run_tests
                    """
                    }
                }
            }
        }
    }
}
