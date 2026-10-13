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
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Syntax Check') {
            steps {
                sh '.venv/bin/python -m compileall -q app.py tests'
            }
        }

        stage('Unit Tests') {
            steps {
                sh '.venv/bin/python -m pytest -v'
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