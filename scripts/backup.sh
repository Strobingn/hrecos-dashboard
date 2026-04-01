#!/bin/bash
# HRECOS Dashboard Backup Script
# Usage: ./scripts/backup.sh [backup_directory]

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="hrecos_backup_${TIMESTAMP}.sql"

echo "🗄️  HRECOS Dashboard Backup"
echo "=========================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "📦 Creating database backup..."
docker compose exec -T db pg_dump -U postgres hrecos > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"
    
    # Compress backup
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    echo "✅ Backup compressed: ${BACKUP_DIR}/${BACKUP_FILE}.gz"
    
    # Cleanup old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "hrecos_backup_*.sql.gz" -mtime +7 -delete
    echo "🧹 Cleaned up backups older than 7 days"
else
    echo "❌ Backup failed"
    exit 1
fi

echo ""
echo "To restore from backup:"
echo "  gunzip < ${BACKUP_DIR}/${BACKUP_FILE}.gz | docker compose exec -T db psql -U postgres hrecos"
