pipeline {
    agent any

    environment {
        DOCKER_IMAGE_GO = "rag-go-api"
        DOCKER_IMAGE_PYTHON = "rag-python-engine"
        DOCKER_IMAGE_UI = "rag-angular-ui"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint & Static Analysis') {
            parallel {
                stage('Python Lint') {
                    steps {
                        sh 'pip install flake8 && flake8 services/ apps/api-python/'
                    }
                }
                stage('Go Lint') {
                    steps {
                        sh 'cd apps/api-go && go vet ./...'
                    }
                }
            }
        }

        stage('Build Containers') {
            steps {
                script {
                    sh "docker compose build"
                }
            }
        }

        stage('Integration Tests') {
            steps {
                script {
                    try {
                        sh "docker compose up -d qdrant postgres"
                        // Wait for services to be ready
                        sh "sleep 10"
                        // Run tests here (e.g., pytest or go test)
                        sh "echo 'Running integration tests...'"
                    } finally {
                        sh "docker compose down"
                    }
                }
            }
        }

        stage('Push / Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh "echo 'Deploying to self-hosted environment...'"
                sh "docker compose up -d"
            }
        }

        stage('Backup Database') {
            steps {
                sh "chmod +x scripts/backup_db.sh"
                sh "./scripts/backup_db.sh"
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
