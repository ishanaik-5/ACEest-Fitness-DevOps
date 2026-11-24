
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
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

        stage('Unit Tests and Coverage') {
            steps {
                sh '''
                    .venv/bin/python -m pytest -v \
                    --cov=app \
                    --cov-report=xml:coverage.xml \
                    --cov-report=term-missing
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    script {
                        def scannerHome = tool 'SonarScanner'
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    script {
                        def qg = waitForQualityGate()
                        if (qg.status != 'OK') {
                            error "Quality Gate failed: ${qg.status}"
                        }
                    }
                }
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
