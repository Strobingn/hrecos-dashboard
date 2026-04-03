#!/bin/bash
# Oracle Cloud Free Tier - HRECOS Dashboard Setup Script
# Run this on your Ubuntu/Oracle Linux VM

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  HRECOS Dashboard - Oracle Cloud Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${YELLOW}Warning: Running as root. Creating user 'hrecos'...${NC}"
   useradd -m -s /bin/bash hrecos 2>/dev/null || true
   usermod -aG sudo hrecos
   echo "hrecos ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/hrecos
   echo -e "${GREEN}User 'hrecos' created. Please switch to that user:${NC}"
   echo "  su - hrecos"
   echo "  cd ~"
   echo "  git clone https://github.com/Strobingn/hrecos-dashboard.git"
   echo "  cd hrecos-dashboard"
   echo "  bash oracle-cloud-setup.sh"
   exit 1
fi

# Get VM's public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/opc/v1/vnics/ | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "YOUR_VM_IP")

echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
sudo apt update -y && sudo apt upgrade -y

echo -e "${YELLOW}Step 2: Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    # Install Docker
    sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update -y
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}Docker installed successfully!${NC}"
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# Install docker-compose standalone
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Installing docker-compose...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo -e "${YELLOW}Step 3: Creating persistent storage...${NC}"
sudo mkdir -p /data/postgres
sudo chown -R $USER:$USER /data

echo -e "${YELLOW}Step 4: Setting up environment...${NC}"
# Generate random passwords if not set
if [ ! -f .env ]; then
    DB_PASS=$(openssl rand -base64 32 2>/dev/null || tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 32)
    SECRET=$(openssl rand -base64 64 2>/dev/null || tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 64)
    
    cat > .env << EOF
DB_PASSWORD=${DB_PASS}
SECRET_KEY=${SECRET}
EOF
    echo -e "${GREEN}Created .env file with secure passwords${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

echo -e "${YELLOW}Step 5: Building and starting services...${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo -e "${YELLOW}Step 6: Waiting for services to start...${NC}"
sleep 10

echo -e "${YELLOW}Step 7: Verifying deployment...${NC}"
# Health checks
MAX_RETRIES=10
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    RETRY=$((RETRY+1))
    echo "  Waiting for backend... ($RETRY/$MAX_RETRIES)"
    sleep 5
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Backend failed to start. Check logs:${NC}"
    echo "  docker logs hrecos-backend"
    exit 1
fi

# Check frontend
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Frontend is responding${NC}"
else
    echo -e "${YELLOW}⚠ Frontend check inconclusive (may need more time)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Access your dashboard:${NC}"
echo "  • Main Dashboard: http://${PUBLIC_IP}"
echo "  • API Health:     http://${PUBLIC_IP}:8000/health"
echo "  • API Docs:       http://${PUBLIC_IP}:8000/docs"
echo ""
echo -e "${YELLOW}Management commands:${NC}"
echo "  View logs:        docker logs -f hrecos-backend"
echo "  Restart:          docker-compose -f docker-compose.prod.yml restart"
echo "  Update:           bash update.sh"
echo "  Stop:             docker-compose -f docker-compose.prod.yml down"
echo ""
echo -e "${YELLOW}To add HTTPS with a free domain:${NC}"
echo "  1. Get free domain at https://duckdns.org"
echo "  2. Edit Caddyfile and uncomment domain section"
echo "  3. docker-compose -f docker-compose.prod.yml restart caddy"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
