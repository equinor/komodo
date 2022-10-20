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
    def isPullRequest = args.pullRequest
    def gitCredentialsID = args.gitCredentialsID
    def agentLabel = params.KOMODO_RELEASE.contains("rhel7") ? "scout-ci7" : "scout-ci"

    pipeline {
        agent { label agentLabel }

        parameters {
            string name: 'GIT_CODE_FORK', defaultValue: 'Equinor'
            string name: 'GIT_CODE_REF', defaultValue: 'main'

            string name: 'GIT_HELPER_FORK', defaultValue: 'Equinor'
            string name: 'GIT_HELPER_REF', defaultValue: 'main'

            string name: 'KOMODO_RELEASE', defaultValue: 'bleeding-py38'
            string(name: 'TEST_SCRIPT', defaultValue: "ci/jenkins/testkomodo.sh", description: 'The custom script for running tests against komodo')
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

            CI_ACTUAL_COMMIT              = "${ghprbActualCommit}"
            CI_ACTUAL_COMMIT_AUTHOR       = "${ghprbActualCommitAuthor}"
            CI_ACTUAL_COMMIT_AUTHOR_EMAIL = "${ghprbActualCommitAuthorEmail}"
            CI_PULL_DESCRIPTION           = "${ghprbPullDescription}"
            CI_PULL_ID                    = "${ghprbPullId}"
            CI_PULL_LINK                  = "${ghprbPullLink}"
            CI_PULL_TITLE                 = "${ghprbPullTitle}"
            CI_SOURCE_BRANCH              = "${ghprbSourceBranch}"
            CI_TARGET_BRANCH              = "${ghprbTargetBranch}"
            CI_COMMENT_BODY               = "${ghprbCommentBody}"
            CI_SHA1                       = "${sha1}"
        }

        stages {
            stage('Pre-setup') {
                steps {
                    deleteDir()

                    // Setup komodoenv
                    sh '''\
                    source ${KOMODO_ROOT}/${CI_KOMODO_RELEASE}/enable
                    komodoenv -r${CI_KOMODO_RELEASE} --no-update test-kenv
                    '''

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
                                    branches: [[name: getVersion(project)]],
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
                        source /opt/rh/rh-git227/enable

                        # Additional CI environment variables
                        export CI_PYTHON_VERSION=\$(python -c 'import sys;print("%s.%s"%sys.version_info[:2])')

                        # Setup colour
                        export CLICOLOR=1
                        export CLICOLOR_FORCE=1
                        export PYTEST_ADDOPTS="--color=yes"

                        source ${env.WORKSPACE}/ci_helper.sh

                        set -x
                        git log -n 1
                        source ${env.CI_SOURCE_ROOT}/${params.TEST_SCRIPT}
                        git log -n 1
                        export MPLBACKEND=agg
                        run_tests
                    """
                    }
                }
            }
        }
    }
}
