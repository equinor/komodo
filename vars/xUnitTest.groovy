def call(Map args = [:]) {
    def job_name = args.job_name
    pipeline {
        agent { label 'master||tr-vresdeploy01.tr.statoil.no||tr-vresdeploy02.tr.statoil.no' }
        options {
            disableConcurrentBuilds()
        }

        parameters {
            string(name: 'RELEASE_BASE', defaultValue: "bleeding", description: 'The release base that is to be tested. I.e. bleeding or 2020.06.05.')
        }

        stages {
            stage('Test Matrix') {
                matrix {
                    agent { label "!(scout-ci || scout-ci7)"}
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
                                ], wait: true
                            }
                        }
                    }
                }
            }
        }
    }
}
