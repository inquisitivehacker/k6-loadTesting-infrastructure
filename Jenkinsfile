pipeline {
    agent any
    tools {
        // This tells Jenkins to use the JDK named 'JDK-21' that you just configured
        jdk 'JDK-21'
    }
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