def call(Map args = [:]) {
    def job_name = args.job_name
    def test_script = "ci/jenkins/testkomodo.sh"
    if (args.test_script) {
        test_script = args.test_script
    }

    pipeline {
        agent any
        options {
            timeout(time: 30, unit: 'MINUTES')
        }

        parameters {
            string(name: 'RELEASE_BASE', defaultValue: "bleeding", description: 'The release base that is to be tested. I.e. bleeding or 2020.06.05.')
        }

        stages {
            stage('Test Matrix') {
                matrix {
                    agent any
                    axes {
                        axis {
                            name 'RH_VERSION'
                            values '7'
                        }
                        axis {
                            name 'PY_VERSION'
                            values '3.6'
                        }
                    }
                    stages {
                        stage('Run PR job') {
                            steps {
                                build job: "${job_name}", parameters: [
                                    string(name: 'KOMODO_RELEASE', value: "${params.RELEASE_BASE}-py${PY_VERSION.replace(".", "")}-rhel${RH_VERSION}"),
                                    string(name: 'ghprbPullId', value: "${params.ghprbPullId}"),
                                    string(name: 'TEST_SCRIPT', value: "${test_script}"),
                                ], wait: true
                            }
                        }
                    }
                }
            }
        }
    }
}
