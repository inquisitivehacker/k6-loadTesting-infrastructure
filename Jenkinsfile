pipeline {
    agent any
    stages {
        stage('Check Java Version') {
            steps {
                sh 'java -version'
            }
        }
        stage('SonarQube Analysis') {
            steps {
                sh 'sonar-scanner'
            }
        }
    }
}