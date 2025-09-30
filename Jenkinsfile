pipeline {
    agent any
    environment {
        JAVA_HOME = '/usr/lib/jvm/java-21-openjdk-amd64'
        PATH = "${JAVA_HOME}/bin:${env.PATH}"
    }
    stages {
        stage('Check Java Version') {
            steps {
                sh 'java -version'
            }
        }
        stage('SonarQube Analysis') {
            steps {
                sh '/usr/lib/jvm/java-21-openjdk-amd64/bin/java -Djava.awt.headless=true -classpath "/opt/sonar-scanner/lib/sonar-scanner-cli-4.8.0.2856.jar" -Dscanner.home="/opt/sonar-scanner" -Dproject.home="$(pwd)" org.sonarsource.scanner.cli.Main'
            }
        }
    }
}