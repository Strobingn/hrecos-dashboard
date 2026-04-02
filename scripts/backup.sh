#!/usr/bin/env bash
#
# HRECOS Dashboard Backup Script
# Usage: ./scripts/backup.sh [OPTIONS]
#   --full      Full backup including database and uploads
#   --db-only   Database backup only
#   --clean     Remove backups older than 30 days
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
FULL=false
DB_ONLY=false
CLEAN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL=true
            shift
            ;;
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --full      Full backup (database + uploads + config)"
            echo "  --db-only   Database backup only (default)"
            echo "  --clean     Remove backups older than 30 days"
            echo "  --help, -h  Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Default to db-only if no options specified
if [[ "${FULL}" == false ]] && [[ "${CLEAN}" == false ]]; then
    DB_ONLY=true
fi

# Setup backup directory
BACKUP_DIR="${REPO_ROOT}/backups"
mkdir -p "${BACKUP_DIR}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="${BACKUP_DIR}/backup-${TIMESTAMP}.log"

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

# Check Docker daemon
check_docker() {
    log "Checking Docker daemon..."
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    success "Docker daemon is running"
}

# Check if database container is running
check_db() {
    if ! docker compose ps | grep -q "hrecos-timescaledb.*running"; then
        error "Database container is not running"
        exit 1
    fi
    success "Database container is running"
}

# Database backup
backup_database() {
    log "Creating database backup..."
    
    local backup_file="${BACKUP_DIR}/hrecos-db-${TIMESTAMP}.sql"
    
    # Get database credentials from .env
    local db_user="${POSTGRES_USER:-hrecos}"
    local db_name="${POSTGRES_DB:-hrecos}"
    
    # Create backup
    if docker compose exec -T timescaledb pg_dump -U "${db_user}" "${db_name}" > "${backup_file}" 2>>"${LOG_FILE}"; then
        success "Database dump created: ${backup_file}"
        
        # Compress
        gzip "${backup_file}"
        success "Backup compressed: ${backup_file}.gz"
        
        # Show size
        local size
        size=$(du -h "${backup_file}.gz" | cut -f1)
        log "Backup size: ${size}"
    else
        error "Database backup failed"
        rm -f "${backup_file}"
        exit 1
    fi
}

# Full backup
backup_full() {
    log "Creating full backup..."
    
    local backup_file="${BACKUP_DIR}/hrecos-full-${TIMESTAMP}.tar.gz"
    local temp_dir="${BACKUP_DIR}/.temp-${TIMESTAMP}"
    
    mkdir -p "${temp_dir}"
    
    # Database backup
    backup_database
    cp "${BACKUP_DIR}/hrecos-db-${TIMESTAMP}.sql.gz" "${temp_dir}/"
    
    # Configuration
    if [[ -f "${REPO_ROOT}/.env" ]]; then
        cp "${REPO_ROOT}/.env" "${temp_dir}/env-backup"
        log "Configuration backed up"
    fi
    
    # Docker compose files
    cp "${REPO_ROOT}/docker-compose.yml" "${temp_dir}/"
    if [[ -f "${REPO_ROOT}/docker-compose.override.yml" ]]; then
        cp "${REPO_ROOT}/docker-compose.override.yml" "${temp_dir}/"
    fi
    
    # Create archive
    tar -czf "${backup_file}" -C "${temp_dir}" . 2>>"${LOG_FILE}"
    
    # Cleanup temp
    rm -rf "${temp_dir}"
    
    success "Full backup created: ${backup_file}"
    
    local size
    size=$(du -h "${backup_file}" | cut -f1)
    log "Full backup size: ${size}"
}

# Cleanup old backups
cleanup_old() {
    log "Cleaning up old backups..."
    
    local count=0
    
    # Remove database backups older than 30 days
    while IFS= read -r file; do
        rm -f "${file}"
        ((count++))
    done < <(find "${BACKUP_DIR}" -name "hrecos-db-*.sql.gz" -type f -mtime +30 2>/dev/null)
    
    # Remove full backups older than 30 days
    while IFS= read -r file; do
        rm -f "${file}"
        ((count++))
    done < <(find "${BACKUP_DIR}" -name "hrecos-full-*.tar.gz" -type f -mtime +30 2>/dev/null)
    
    # Remove old log files
    find "${BACKUP_DIR}" -name "backup-*.log" -type f -mtime +7 -delete 2>/dev/null || true
    
    success "Removed ${count} old backup files"
    
    # Show disk usage
    local usage
    usage=$(du -sh "${BACKUP_DIR}" | cut -f1)
    log "Total backup directory size: ${usage}"
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [[ -n $(find "${BACKUP_DIR}" -name "*.gz" -o -name "*.tar.gz" 2>/dev/null) ]]; then
        echo ""
        echo "Database backups:"
        find "${BACKUP_DIR}" -name "hrecos-db-*.sql.gz" -printf "  %f (%s bytes)\n" 2>/dev/null | sort -r | head -5
        
        echo ""
        echo "Full backups:"
        find "${BACKUP_DIR}" -name "hrecos-full-*.tar.gz" -printf "  %f (%s bytes)\n" 2>/dev/null | sort -r | head -5
    else
        echo "  No backups found"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Backup Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Timestamp: ${TIMESTAMP}"
    echo "Location:  ${BACKUP_DIR}"
    echo "Log:       ${LOG_FILE}"
    echo ""
    echo "To restore a backup:"
    echo "  gunzip < backup-file.sql.gz | docker compose exec -T timescaledb psql -U hrecos"
    echo ""
}

# Main
main() {
    log "HRECOS Dashboard Backup"
    log "Repository: ${REPO_ROOT}"
    log "Mode: $([[ ${FULL} == true ]] && echo 'FULL' || ([[ ${DB_ONLY} == true ]] && echo 'DATABASE ONLY' || echo 'CLEANUP ONLY'))"
    
    check_docker
    
    if [[ "${CLEAN}" == true ]]; then
        cleanup_old
    fi
    
    if [[ "${FULL}" == true ]]; then
        check_db
        backup_full
    elif [[ "${DB_ONLY}" == true ]]; then
        check_db
        backup_database
    fi
    
    list_backups
    print_summary
}

main "$@"
