#!/usr/bin/env bash
#
# HRECOS Dashboard Production Deployment Script
# Usage: ./scripts/deploy.sh [OPTIONS]
#   --prod      Deploy to production (required)
#   --dry-run   Show what would be deployed without deploying
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# Options
PROD=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            PROD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --prod      Deploy to production (required for safety)"
            echo "  --dry-run   Show what would be deployed without deploying"
            echo "  --help, -h  Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Logging
mkdir -p "${REPO_ROOT}/logs"
mkdir -p "${REPO_ROOT}/backups"
LOG_FILE="${REPO_ROOT}/logs/deploy-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "${LOG_FILE}"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "${LOG_FILE}"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "${LOG_FILE}"
}

# Safety check
if [[ "${PROD}" != true ]] && [[ "${DRY_RUN}" != true ]]; then
    error "Must specify --prod for production deployment or --dry-run for dry run"
    echo "This is a safety measure. Use --prod to confirm you want to deploy."
    exit 1
fi

# Verify Docker daemon
check_docker() {
    log "Checking Docker daemon..."
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    success "Docker daemon is running"
}

# Pre-deployment checks
run_checks() {
    log "Running pre-deployment checks..."
    
    # Check .env exists
    if [[ ! -f "${REPO_ROOT}/.env" ]]; then
        error ".env file not found. Run setup.sh first."
        exit 1
    fi
    success ".env file exists"
    
    # Check docker-compose.yml exists
    if [[ ! -f "${REPO_ROOT}/docker-compose.yml" ]]; then
        error "docker-compose.yml not found"
        exit 1
    fi
    success "docker-compose.yml exists"
    
    # Validate docker-compose syntax
    if ! docker compose config > /dev/null 2>&1; then
        error "docker-compose.yml has syntax errors"
        exit 1
    fi
    success "docker-compose.yml is valid"
    
    # Check git status
    if [[ -d "${REPO_ROOT}/.git" ]]; then
        local branch
        branch=$(git rev-parse --abbrev-ref HEAD)
        log "Current branch: ${branch}"
        
        if [[ -n $(git status --porcelain) ]]; then
            warn "Uncommitted changes detected:"
            git status --short | tee -a "${LOG_FILE}"
        else
            success "Working directory is clean"
        fi
    fi
}

# Backup database before deployment
backup_database() {
    log "Creating database backup..."
    
    local backup_name="pre-deploy-$(date +%Y%m%d-%H%M%S).sql"
    local backup_path="${REPO_ROOT}/backups/${backup_name}"
    
    # Check if postgres container is running
    if docker compose ps | grep -q "hrecos-timescaledb"; then
        if docker compose exec -T timescaledb pg_dump -U hrecos hrecos > "${backup_path}" 2>/dev/null; then
            success "Database backed up to backups/${backup_name}"
            gzip "${backup_path}"
        else
            warn "Database backup failed (container may not be ready)"
        fi
    else
        warn "Database container not running, skipping backup"
    fi
}

# Deploy
deploy() {
    log "Starting deployment..."
    
    if [[ "${DRY_RUN}" == true ]]; then
        log "[DRY RUN] Would pull latest images"
        log "[DRY RUN] Would build services"
        log "[DRY RUN] Would restart services"
        success "Dry run complete - no changes made"
        return 0
    fi
    
    # Pull latest images if using pre-built
    # docker compose pull 2>&1 | tee -a "${LOG_FILE}"
    
    # Build and deploy
    log "Building and deploying services..."
    docker compose up -d --build 2>&1 | tee -a "${LOG_FILE}"
    success "Services deployed"
    
    # Wait for services
    log "Waiting for services to stabilize..."
    sleep 10
    
    # Health check
    log "Running health checks..."
    local attempts=0
    local max_attempts=30
    
    while [[ ${attempts} -lt ${max_attempts} ]]; do
        if curl -sf http://localhost:8000/health &> /dev/null; then
            success "Backend is healthy"
            break
        fi
        ((attempts++))
        log "Health check ${attempts}/${max_attempts}..."
        sleep 2
    done
    
    if [[ ${attempts} -eq ${max_attempts} ]]; then
        error "Health check failed - deployment may have issues"
        docker compose logs --tail=50 >> "${LOG_FILE}"
        exit 1
    fi
}

# Cleanup old backups and logs
cleanup() {
    log "Cleaning up old files..."
    
    # Keep last 30 days of backups
    find "${REPO_ROOT}/backups" -name "*.sql.gz" -type f -mtime +30 -delete 2>/dev/null || true
    success "Old backups cleaned"
    
    # Keep last 90 days of logs
    find "${REPO_ROOT}/logs" -name "*.log" -type f -mtime +90 -delete 2>/dev/null || true
    success "Old logs cleaned"
}

# Print deployment summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Timestamp: $(date)"
    echo "Log:       ${LOG_FILE}"
    echo ""
    echo "Services:"
    docker compose ps
    echo ""
    echo "To rollback: docker compose down && git checkout <commit> && $0 --prod"
    echo ""
}

# Main
main() {
    log "HRECOS Dashboard Deployment"
    log "Repository: ${REPO_ROOT}"
    log "Mode: $([[ ${DRY_RUN} == true ]] && echo 'DRY RUN' || echo 'PRODUCTION')"
    
    check_docker
    run_checks
    backup_database
    deploy
    cleanup
    print_summary
}

main "$@"
