@Library('my-shared-library') _

pipeline {
    agent { label 'debian-master' }
    stages {
        stage('Run SonarQube Analysis') {
            steps {
                checkout scm
                sonarScan()
            }
        }
    }
}