#!/bin/bash

# Rollback script for the scraping system
# Usage: ./rollback.sh <environment> <version>

set -e

ENVIRONMENT=$1
VERSION=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./rollback.sh <environment> <version>"
    echo "Example: ./rollback.sh staging v1.0.0"
    exit 1
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "Invalid environment. Must be 'staging' or 'production'"
    exit 1
fi

# Load environment-specific configuration
source "config/${ENVIRONMENT}.env"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a version exists
check_version() {
    local version=$1
    if ! docker image inspect "ghcr.io/${GITHUB_REPOSITORY}:${version}" >/dev/null 2>&1; then
        log "Error: Version ${version} not found"
        exit 1
    fi
}

# Function to backup current state
backup_state() {
    log "Backing up current state..."
    timestamp=$(date +'%Y%m%d_%H%M%S')
    backup_dir="backups/${ENVIRONMENT}/${timestamp}"
    
    mkdir -p "$backup_dir"
    
    # Backup database
    pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "${backup_dir}/database.sql"
    
    # Backup configuration
    cp "config/${ENVIRONMENT}.env" "${backup_dir}/config.env"
    
    # Backup current version
    docker-compose config > "${backup_dir}/docker-compose.yml"
    
    log "Backup completed: ${backup_dir}"
}

# Function to perform rollback
perform_rollback() {
    log "Starting rollback to version ${VERSION}..."
    
    # Stop current containers
    log "Stopping current containers..."
    docker-compose down
    
    # Pull the specified version
    log "Pulling version ${VERSION}..."
    docker-compose pull
    
    # Update docker-compose.yml with the specified version
    sed -i "s/image: ghcr.io\/${GITHUB_REPOSITORY}:.*/image: ghcr.io\/${GITHUB_REPOSITORY}:${VERSION}/" docker-compose.yml
    
    # Start containers with the rolled back version
    log "Starting containers with version ${VERSION}..."
    docker-compose up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    timeout=300
    while [ $timeout -gt 0 ]; do
        if docker-compose ps | grep -q "healthy"; then
            log "Services are healthy"
            break
        fi
        sleep 5
        timeout=$((timeout-5))
    done
    
    if [ $timeout -le 0 ]; then
        log "Error: Services failed to become healthy"
        exit 1
    fi
}

# Main execution
log "Starting rollback process for ${ENVIRONMENT} to version ${VERSION}"

# Check if version exists
check_version "$VERSION"

# Create backup
backup_state

# Perform rollback
perform_rollback

log "Rollback completed successfully" 