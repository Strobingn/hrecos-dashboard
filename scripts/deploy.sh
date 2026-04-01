#!/bin/bash
# HRECOS Dashboard Deployment Script
# Usage: ./scripts/deploy.sh [production|staging]

ENV="${1:-production}"

echo "🚀 Deploying HRECOS Dashboard to $ENV"
echo "====================================="
echo ""

# Verify environment
echo "🔍 Verifying environment..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

if [ "$ENV" = "production" ]; then
    echo "⚠️  WARNING: Deploying to PRODUCTION"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

echo ""

# Pull latest images
echo "⬇️  Pulling latest images..."
docker compose pull

# Deploy
echo "🔄 Deploying services..."
docker compose up -d --remove-orphans

# Health check
echo "🏥 Performing health check..."
sleep 10

if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker compose logs backend --tail=50
    exit 1
fi

if curl -sf http://localhost:8080 > /dev/null; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
    exit 1
fi

# Cleanup
echo "🧹 Cleaning up old images..."
docker image prune -af

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo "📖 API Docs:  http://localhost:8000/docs"
echo ""
