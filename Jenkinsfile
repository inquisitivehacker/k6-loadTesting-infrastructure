pipeline {
    agent any

    tools {
        // Defines the JDK for the whole pipeline
        jdk 'JDK-21' // Make sure this matches the name in your Global Tool Config
    }

    stages {
        // The automatic checkout from Git happens here
        
        stage('Run SonarQube Analysis') {
            // This environment block forces the correct JAVA_HOME for this stage
            environment {
                // 'tool' gets the path you configured in Jenkins.
                // We assign that path to JAVA_HOME.
                JAVA_HOME = tool 'JDK-21' 
                // We add the new Java's bin directory to the system PATH.
                PATH = "${JAVA_HOME}/bin:${env.PATH}"
            }
            steps {
                withSonarQubeEnv('SonarQube-Server') { 
                    // Now, this command will run using the correct Java version
                    sh 'sonar-scanner' 
                }
            }
        }
    }
}