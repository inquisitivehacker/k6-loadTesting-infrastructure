pipeline {
    agent any

    stages {
        stage('Checkout from Git') {
            steps {
                checkout scm
            }
        }

        stage('Run SonarQube Analysis') {
            steps {
                // Use the SonarQube server you configured in Jenkins
                withSonarQubeEnv('SonarQube-Server') { 
                    sh 'sonar-scanner' 
                }
            }
        }
    }
}