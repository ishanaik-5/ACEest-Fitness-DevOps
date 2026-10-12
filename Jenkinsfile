pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Clean Workspace and Checkout') {
            steps {
                cleanWs()
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m pip install --user -r requirements.txt'
            }
        }

        stage('Syntax Check') {
            steps {
                sh 'python3 -m compileall -q app.py tests'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'python3 -m pytest -v'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build --tag aceest-fitness:jenkins .'
            }
        }
    }

    post {
        always {
            echo 'ACEest Fitness build pipeline finished. Review stage results above.'
        }
    }
}
