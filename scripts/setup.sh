#!/usr/bin/env bash
#
# HRECOS Dashboard Setup Script
# Usage: ./scripts/setup.sh [OPTIONS]
#   --up          Build and start services
#   --no-build    Skip build, just start
#   --force-env   Recreate .env from .env.example
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Change to repo root
cd "${REPO_ROOT}"

# Default options
UP=false
NO_BUILD=false
FORCE_ENV=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --up)
            UP=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --force-env)
            FORCE_ENV=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --up          Build images and start services"
            echo "  --no-build    Skip build, just start services"
            echo "  --force-env   Recreate .env from .env.example"
            echo "  --help, -h    Show this help message"
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
LOG_FILE="${REPO_ROOT}/logs/setup-$(date +%Y%m%d-%H%M%S).log"

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

# Check if Docker is installed
check_docker() {
    log "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    success "Docker and Docker Compose are installed"
}

# Check if Docker daemon is running
check_docker_daemon() {
    log "Checking Docker daemon..."
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    success "Docker daemon is running"
}

# Setup environment file
setup_env() {
    log "Setting up environment..."
    
    if [[ "${FORCE_ENV}" == true ]] && [[ -f "${REPO_ROOT}/.env" ]]; then
        log "Force-env requested: backing up existing .env"
        cp "${REPO_ROOT}/.env" "${REPO_ROOT}/backups/.env.backup-$(date +%Y%m%d-%H%M%S)"
        rm "${REPO_ROOT}/.env"
    fi
    
    if [[ ! -f "${REPO_ROOT}/.env" ]]; then
        if [[ -f "${REPO_ROOT}/.env.example" ]]; then
            cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
            success "Created .env from .env.example"
            warn "Please review and update .env with your settings"
        else
            error ".env.example not found!"
            exit 1
        fi
    else
        success ".env already exists (use --force-env to recreate)"
    fi
}

# Validate environment variables
validate_env() {
    log "Validating environment..."
    
    # Source the .env file
    set -a
    source "${REPO_ROOT}/.env"
    set +a
    
    local warnings=0
    
    # Check email configuration if enabled
    if [[ "${EMAIL_ENABLED:-false}" == "true" ]]; then
        if [[ -z "${SMTP_USER:-}" ]] || [[ -z "${SMTP_PASS:-}" ]]; then
            warn "EMAIL_ENABLED=true but SMTP_USER or SMTP_PASS is empty"
            ((warnings++))
        fi
    fi
    
    # Check SMS configuration if enabled
    if [[ "${SMS_ENABLED:-false}" == "true" ]]; then
        if [[ -z "${TWILIO_SID:-}" ]] || [[ -z "${TWILIO_TOKEN:-}" ]]; then
            warn "SMS_ENABLED=true but TWILIO_SID or TWILIO_TOKEN is empty"
            ((warnings++))
        fi
    fi
    
    # Check Slack configuration if enabled
    if [[ "${SLACK_ENABLED:-false}" == "true" ]]; then
        if [[ -z "${SLACK_WEBHOOK:-}" ]]; then
            warn "SLACK_ENABLED=true but SLACK_WEBHOOK is empty"
            ((warnings++))
        fi
    fi
    
    if [[ ${warnings} -eq 0 ]]; then
        success "Environment validation passed"
    else
        warn "Environment validation completed with ${warnings} warning(s)"
    fi
}

# Build Docker images
build_images() {
    if [[ "${NO_BUILD}" == true ]]; then
        log "Skipping build (--no-build specified)"
        return 0
    fi
    
    log "Building Docker images..."
    docker compose build --no-cache 2>&1 | tee -a "${LOG_FILE}"
    success "Docker images built successfully"
}

# Start services
start_services() {
    if [[ "${UP}" == false ]]; then
        log "Use --up to start services"
        return 0
    fi
    
    log "Starting services..."
    
    if [[ "${NO_BUILD}" == true ]]; then
        docker compose up -d 2>&1 | tee -a "${LOG_FILE}"
    else
        docker compose up -d --build 2>&1 | tee -a "${LOG_FILE}"
    fi
    
    success "Services started"
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 5
    
    # Check backend health
    local attempts=0
    local max_attempts=30
    
    while [[ ${attempts} -lt ${max_attempts} ]]; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            success "Backend is healthy"
            break
        fi
        ((attempts++))
        log "Waiting for backend... (${attempts}/${max_attempts})"
        sleep 2
    done
    
    if [[ ${attempts} -eq ${max_attempts} ]]; then
        warn "Backend health check timed out"
    fi
    
    # Check frontend
    if curl -s http://localhost:8080 &> /dev/null; then
        success "Frontend is accessible"
    else
        warn "Frontend not yet accessible"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  HRECOS Dashboard Setup Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Services:"
    echo "  Dashboard: http://localhost:8080"
    echo "  API:       http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  Database:  localhost:5432"
    echo ""
    echo "Logs: ${LOG_FILE}"
    echo ""
    
    if [[ "${UP}" == true ]]; then
        echo "To stop services: docker compose down"
        echo "To view logs:     docker compose logs -f"
    fi
    
    echo ""
}

# Main execution
main() {
    log "Starting HRECOS Dashboard setup..."
    log "Repository root: ${REPO_ROOT}"
    
    check_docker
    check_docker_daemon
    setup_env
    validate_env
    build_images
    start_services
    
    print_summary
}

main "$@"
