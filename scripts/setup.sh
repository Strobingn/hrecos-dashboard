#!/bin/bash
# HRECOS Dashboard Setup Script
# Usage: ./scripts/setup.sh

set -e

echo "🌊 HRECOS Dashboard Setup"
echo "========================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Setup environment
echo "🔧 Setting up environment..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo "⚠️  Please edit .env file with your configuration before starting"
    else
        echo "❌ .env.example file not found"
        exit 1
    fi
else
    echo "✅ .env file already exists"
fi

echo ""

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
echo "✅ Directories created"
echo ""

# Build and start
echo "🐳 Building Docker images..."
docker compose build
echo ""

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your configuration"
echo "  2. Run: docker compose up -d"
echo "  3. Access dashboard at: http://localhost:8080"
echo "  4. API docs at: http://localhost:8000/docs"
echo ""
