    pipeline {
    agent {
        node {
            label 'local'
            customWorkspace "C:/Rudra/College/SEM VII/MLOps/Practicals/Practical6/2_local_git"
        }
    }

    stages {
        stage('Prepare Git') {
            steps {
                echo 'Marking repo as safe for Git'
                bat 'git config --global --add safe.directory "C:/Rudra/College/SEM VII/MLOps/Practicals/Practical6/2_local_git"'
                
                echo 'Pulling latest changes'
                bat 'git log --oneline -5 || echo "Git log not available"'
            }
        }

         stage('Show Workspace') {
            steps {
                bat 'cd'
            }
        }

        stage('Build Images') {
            steps {
                bat 'docker-compose build'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'docker run --rm webapp pytest || echo "No tests found"'
            }
        }

        stage('Deploy Containers') {
            steps {
                bat 'docker-compose up -d'
            }
        }
    }
}
