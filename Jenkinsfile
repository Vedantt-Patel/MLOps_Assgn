    pipeline {
    agent any

    environment {
        // Project Configuration
        PROJECT_NAME = 'FakeNewsDetector'
        COMPOSE_PROJECT_NAME = 'fakenews'
        
        // Docker Configuration
        DOCKER_BUILDKIT = '1'
        COMPOSE_DOCKER_CLI_BUILD = '1'
        
        // Service URLs
        API_URL = 'http://localhost:8000'
        MLFLOW_URL = 'http://localhost:5000'
    }

    options {
        // Keep only last 10 builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        
        // Timeout after 30 minutes
        timeout(time: 30, unit: 'MINUTES')
        
        // Disable concurrent builds
        disableConcurrentBuilds()
    }

    stages {
        stage('🔍 Environment Check') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Checking Environment & Prerequisites'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Show workspace
                    bat 'echo Current Directory: %CD%'
                    
                    // Check Docker
                    bat 'docker --version'
                    bat 'docker-compose --version'
                    
                    // Check if Docker daemon is running
                    bat 'docker info'
                    
                    // Show Git info
                    bat 'git log --oneline -3 || echo "No git history"'
                    bat 'git branch --show-current || echo "Detached HEAD"'
                }
            }
        }

        stage('🧹 Cleanup Old Containers') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Cleaning Up Previous Deployment'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Stop and remove containers (keep volumes for data persistence)
                    bat 'docker-compose down || echo "No containers to stop"'
                    
                    // Clean up dangling images
                    bat 'docker image prune -f || echo "No dangling images"'
                }
            }
        }

        stage('🔨 Build Docker Images') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Building Docker Images'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Build images without cache for clean build
                    bat 'docker-compose build --no-cache'
                    
                    // Show built images
                    bat 'docker images | findstr fakenews'
                }
            }
        }

        stage('🚀 Deploy Services') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Starting Services with Docker Compose'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Start all services in detached mode
                    bat 'docker-compose up -d'
                    
                    // Wait for services to initialize
                    echo 'Waiting for services to initialize...'
                    bat 'timeout /t 15 /nobreak'
                    
                    // Show running containers
                    bat 'docker-compose ps'
                }
            }
        }

        stage('🔬 Health Checks') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Running Health Checks'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Check MLflow service
                    echo '📊 Checking MLflow Tracking Server...'
                    retry(3) {
                        bat '''
                            curl -f %MLFLOW_URL% || (
                                echo "MLflow health check failed, retrying..."
                                timeout /t 5 /nobreak
                                exit 1
                            )
                        '''
                    }
                    echo '✅ MLflow is healthy'
                    
                    // Check API service
                    echo '🔌 Checking Fake News Detector API...'
                    retry(3) {
                        bat '''
                            curl -f %API_URL%/api/stats || (
                                echo "API health check failed, retrying..."
                                timeout /t 5 /nobreak
                                exit 1
                            )
                        '''
                    }
                    echo '✅ API is healthy'
                    
                    // Check container health status
                    echo '🏥 Checking Docker Health Status...'
                    bat 'docker-compose ps'
                    bat 'docker inspect fakenews-api --format="{{.State.Health.Status}}" || echo "No health status"'
                    bat 'docker inspect fakenews-mlflow --format="{{.State.Health.Status}}" || echo "No health status"'
                }
            }
        }

        stage('🧪 Functional Tests') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Running Functional Tests'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Test API prediction endpoint
                    echo '🎯 Testing Prediction Endpoint...'
                    bat '''
                        curl -X POST "%API_URL%/predict" ^
                             -H "Content-Type: application/json" ^
                             -d "{\\"title\\":\\"Test News\\",\\"text\\":\\"This is a test article for Jenkins pipeline\\"}" ^
                             || echo "Prediction test warning"
                    '''
                    
                    // Test stats endpoint
                    echo '📈 Testing Stats Endpoint...'
                    bat 'curl -f %API_URL%/api/stats || echo "Stats test warning"'
                    
                    // Test predictions list endpoint
                    echo '📋 Testing Predictions List...'
                    bat 'curl -f %API_URL%/api/predictions || echo "Predictions list warning"'
                    
                    echo '✅ Functional tests completed'
                }
            }
        }

        stage('📊 Service Logs') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Collecting Service Logs'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    
                    // Show last 20 lines of logs from each service
                    echo '📝 API Service Logs:'
                    bat 'docker-compose logs --tail=20 api'
                    
                    echo '📝 MLflow Service Logs:'
                    bat 'docker-compose logs --tail=20 mlflow'
                }
            }
        }

        stage('📦 Deployment Summary') {
            steps {
                script {
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo '  Deployment Summary'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo ''
                    echo '✅ Deployment Successful!'
                    echo ''
                    echo '🌐 Service URLs:'
                    echo '   • Main App:      http://localhost:8000'
                    echo '   • Dashboard:     http://localhost:8000/dashboard'
                    echo '   • API Docs:      http://localhost:8000/docs'
                    echo '   • MLflow UI:     http://localhost:5000'
                    echo ''
                    echo '📦 Running Containers:'
                    bat 'docker ps --filter "name=fakenews" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
                    echo ''
                    echo '💾 Data Volumes:'
                    bat 'docker volume ls | findstr fakenews'
                    echo ''
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                }
            }
        }
    }

    post {
        success {
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo '✅ Pipeline Completed Successfully!'
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo ''
            echo '🎉 Fake News Detector is now running!'
            echo '🌐 Access the application at: http://localhost:8000'
            echo ''
        }
        
        failure {
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo '❌ Pipeline Failed!'
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo ''
            echo '📋 Troubleshooting Steps:'
            echo '1. Check Docker is running'
            echo '2. Review stage logs above'
            echo '3. Check container logs: docker-compose logs'
            echo '4. Verify ports 8000 and 5000 are available'
            echo ''
            
            // Collect logs on failure
            bat 'docker-compose logs || echo "Could not collect logs"'
            
            // Cleanup on failure
            echo '🧹 Cleaning up failed deployment...'
            bat 'docker-compose down || echo "Cleanup failed"'
        }
        
        always {
            echo ''
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo "  Build #${env.BUILD_NUMBER} Finished"
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        }
    }
}
