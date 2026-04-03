#!/bin/bash
# HRECOS Dashboard Update Script for Oracle Cloud

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Updating HRECOS Dashboard...${NC}"

# Pull latest code
echo -e "${YELLOW}Pulling latest code from GitHub...${NC}"
git pull origin main

# Backup database before update
echo -e "${YELLOW}Creating database backup...${NC}"
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec hrecos-db pg_dump -U postgres hrecos > "backups/$BACKUP_FILE" 2>/dev/null || echo "Backup skipped (DB may not be running)"

# Build and restart
echo -e "${YELLOW}Rebuilding containers...${NC}"
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo -e "${YELLOW}Waiting for services...${NC}"
sleep 10

# Health check
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Update successful!${NC}"
    echo "  Dashboard: http://$(curl -s http://169.254.169.254/opc/v1/vnics/ | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
else
    echo -e "${YELLOW}⚠ Services starting, check logs with: docker logs hrecos-backend${NC}"
fi
