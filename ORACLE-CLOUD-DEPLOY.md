# Oracle Cloud Free Tier Deployment Guide

Deploy HRECOS Dashboard on Oracle Cloud's **Always Free** tier (4GB ARM VM).

## 📋 Prerequisites

- Oracle Cloud account (free tier)
- SSH key pair
- GitHub repo access

---

## 🚀 Quick Deploy (One Command)

### Step 1: Create VM in Oracle Cloud Console

1. Go to https://cloud.oracle.com
2. **Compute** → **Instances** → **Create Instance**
3. Settings:
   ```
   Name: hrecos-server
   Image: Ubuntu 22.04
   Shape: VM.Standard.A1.Flex (ARM)
   OCPUs: 1
   Memory: 4 GB
   Boot Volume: 50 GB
   ```
4. Add SSH key (generate new or upload public key)
5. Create

### Step 2: Configure Security Rules

1. **Networking** → **Virtual Cloud Networks** → Your VCN
2. **Subnets** → Default Subnet
3. **Security Lists** → Default Security List
4. **Add Ingress Rules**:
   | Source | Protocol | Port | Description |
   |--------|----------|------|-------------|
   | 0.0.0.0/0 | TCP | 22 | SSH |
   | 0.0.0.0/0 | TCP | 80 | HTTP |
   | 0.0.0.0/0 | TCP | 443 | HTTPS |
   | 0.0.0.0/0 | TCP | 8000 | API (optional) |

### Step 3: SSH and Deploy

Get your VM's public IP from the Oracle console, then:

```bash
# SSH into VM
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_VM_PUBLIC_IP

# Clone repo
git clone https://github.com/Strobingn/hrecos-dashboard.git
cd hrecos-dashboard

# Run automated setup
bash oracle-cloud-setup.sh
```

That's it! 🎉

---

## 🔧 Manual Setup (If Script Fails)

```bash
# Install Docker
sudo apt update && sudo apt install -y docker.io docker-compose git
sudo systemctl start docker
sudo usermod -aG docker $USER

# Create storage
sudo mkdir -p /data/postgres
sudo chown -R $USER:$USER /data

# Create .env
cat > .env << 'EOF'
DB_PASSWORD=your-secure-password-here
SECRET_KEY=your-secret-key-min-32-chars
EOF

# Deploy
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 🌐 Access Your Dashboard

After deployment:

| Service | URL |
|---------|-----|
| Dashboard | `http://YOUR_VM_IP` |
| API Health | `http://YOUR_VM_IP:8000/health` |
| API Docs | `http://YOUR_VM_IP:8000/docs` |
| Backend Direct | `http://YOUR_VM_IP:8000` |

---

## 🔒 Adding HTTPS (Free Domain)

### 1. Get Free Domain from DuckDNS

1. Go to https://duckdns.org
2. Sign in with GitHub/Google
3. Create a subdomain: `yourname.duckdns.org`
4. Copy your token

### 2. Update DNS to Point to Your VM

```bash
# Install DuckDNS client
mkdir -p ~/duckdns
cd ~/duckdns
cat > duck.sh << 'EOF'
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -
EOF
chmod +x duck.sh

# Run every 5 minutes
crontab -l 2>/dev/null | { cat; echo "*/5 * * * * ~/duckdns/duck.sh"; } | crontab -
```

### 3. Enable HTTPS in Caddyfile

```bash
# Edit Caddyfile
nano Caddyfile
```

Replace contents with:
```
your-domain.duckdns.org {
    encode gzip
    
    handle /api/* {
        reverse_proxy backend:8000
    }
    
    handle /health {
        reverse_proxy backend:8000
    }
    
    handle /* {
        reverse_proxy frontend:80
    }
}
```

### 4. Restart Caddy

```bash
docker-compose -f docker-compose.prod.yml restart caddy
```

Your site is now at: `https://your-domain.duckdns.org` with automatic HTTPS!

---

## 📊 Resource Usage

| Service | Memory Limit | CPU |
|---------|--------------|-----|
| Database | 512 MB | Shared |
| Backend | 512 MB | Shared |
| Frontend | 128 MB | Shared |
| Caddy | 128 MB | Shared |
| **Total** | **~1.3 GB** | **Minimal** |

Plenty of room on the 4GB free tier VM!

---

## 🔧 Management Commands

```bash
# View logs
docker logs -f hrecos-backend
docker logs -f hrecos-frontend
docker logs -f hrecos-db

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Update to latest code
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# Or use the update script
bash oracle-cloud-update.sh

# Backup database
docker exec hrecos-db pg_dump -U postgres hrecos > backup.sql

# Restore database
cat backup.sql | docker exec -i hrecos-db psql -U postgres -d hrecos

# Check resource usage
docker stats

# Stop everything
docker-compose -f docker-compose.prod.yml down

# Free up space (remove old images)
docker system prune -a
```

---

## 🐛 Troubleshooting

### Port 80 already in use
```bash
# Find process using port 80
sudo lsof -i :80
# Kill it or change port in docker-compose.prod.yml
```

### Out of memory
```bash
# Check memory
docker stats --no-stream

# Restart with memory limits
docker-compose -f docker-compose.prod.yml restart

# Free memory
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

### Database won't start
```bash
# Check disk space
df -h

# Fix permissions
sudo chown -R 999:999 /data/postgres

# Reset (WARNING: deletes all data!)
sudo rm -rf /data/postgres/*
docker-compose -f docker-compose.prod.yml restart db
```

### Can't access from browser
```bash
# Check security rules in Oracle Console
# Ensure ports 80, 443, 8000 are open in VCN Security List

# Test locally on VM
curl http://localhost:8000/health
curl http://localhost

# Check if services are running
docker ps
```

---

## 🔐 Security Recommendations

1. **Change default passwords** in `.env`
2. **Disable password auth** for SSH, use keys only
3. **Enable Oracle Cloud firewall** (in addition to VCN rules)
4. **Set up automated backups**:
   ```bash
   # Daily database backup
   0 2 * * * docker exec hrecos-db pg_dump -U postgres hrecos > ~/backups/hrecos_$(date +\%Y\%m\%d).sql
   ```

---

## 📈 Monitoring

```bash
# CPU/Memory usage
htop

# Disk usage
df -h
du -sh /data/postgres

# Container stats
docker stats --no-stream

# Check logs for errors
docker logs --tail 100 hrecos-backend | grep -i error
```

---

## 🆘 Getting Help

- **Oracle Cloud Issues:** https://docs.oracle.com/en-us/iaas/Content/GSG/Concepts/getstarted.htm
- **Docker Issues:** `docker logs <container-name>`
- **HRECOS Issues:** Check GitHub issues or API logs

---

## ✅ Free Tier Limits (Won't Expire)

| Resource | Limit |
|----------|-------|
| ARM VM | 4 OCPUs, 24GB RAM |
| Storage | 200GB |
| Bandwidth | 10TB/month |
| **Cost** | **$0 Forever** |

---

Ready to deploy? Start with **Step 1** above! 🚀
