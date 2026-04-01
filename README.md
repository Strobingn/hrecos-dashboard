# 🌊 HRECOS Dashboard

Real-time environmental monitoring dashboard for the **Hudson River Environmental Conditions Observing System (HRECOS)**.

[![CI](https://github.com/bass/hrecos-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/bass/hrecos-dashboard/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/bass/hrecos-dashboard/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/bass/hrecos-dashboard/actions/workflows/docker-publish.yml)
[![Security Scan](https://github.com/bass/hrecos-dashboard/actions/workflows/security-scan.yml/badge.svg)](https://github.com/bass/hrecos-dashboard/actions/workflows/security-scan.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-5D3FD3?style=flat)](https://www.timescale.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

## 📋 Features

- 🔄 **Real-time Data Ingestion** - Automatic fetching from HRECOS monitoring stations every 10 minutes
- 📊 **Interactive Dashboard** - Live charts, maps, and station status
- 🤖 **AI Anomaly Detection** - Machine learning-powered outlier detection using Isolation Forest
- 🚨 **Multi-channel Alerts** - Email, SMS (Twilio), and Slack notifications
- 🗄️ **Time-series Database** - TimescaleDB for efficient storage and querying
- 🐳 **Dockerized Stack** - One-command deployment with Docker Compose
- 🔒 **Security First** - Automated security scanning and dependency updates
- 🚀 **CI/CD Ready** - GitHub Actions for testing, building, and deployment

## 🏗️ Architecture

```
hrecos-dashboard/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── main.py       # API endpoints
│   │   ├── models.py     # Database models
│   │   ├── hr_data.py    # HRECOS API integration
│   │   ├── tasks.py      # Background scheduler
│   │   ├── anomalies.py  # ML anomaly detection
│   │   └── alerts.py     # Notification system
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          # HTML/JS dashboard
│   └── index.html
├── .github/           # GitHub Actions & templates
│   ├── workflows/      # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/ # Issue templates
│   └── ...
├── scripts/           # Helper scripts
│   ├── setup.sh
│   ├── backup.sh
│   └── deploy.sh
├── docker-compose.yml # Infrastructure orchestration
├── Makefile          # Development commands
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Deploy

```bash
# Clone the repository
git clone https://github.com/bass/hrecos-dashboard.git
cd hrecos-dashboard

# Quick setup with helper script
./scripts/setup.sh

# Or manual setup
cp .env.example .env

# Start the stack
docker compose up --build

# Or run in background
docker compose up -d --build
```

### Access the Dashboard

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:8080 | Main web interface |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| API | http://localhost:8000 | REST API endpoints |
| Database | localhost:5432 | PostgreSQL/TimescaleDB |

## 🛠️ Development

### Makefile Commands

```bash
# Development
make build        # Build all Docker images
make up           # Start all services
make up-d         # Start services in detached mode
make down         # Stop all services
make logs         # View logs
make logs-backend # View backend logs only

# Code quality
make lint         # Run linters (flake8, black, isort)
make format       # Format code with black
make test         # Run tests

# Database
make db-shell     # Open PostgreSQL shell
make db-reset     # Reset database (WARNING: deletes data)

# Deployment
make deploy       # Deploy to production via GitHub Actions
make clean        # Remove containers and volumes

# Utilities
make health       # Check service health
make api-test     # Test API endpoints
```

### Local Development (without Docker)

```bash
# Setup Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database (requires PostgreSQL 14+)
createdb hrecos

# Start backend
uvicorn app.main:app --reload

# Frontend (serve with any static server)
cd ../frontend
python -m http.server 8080
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/hrecos

# Email Alerts (Gmail SMTP)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
ALERT_EMAIL=recipient@example.com

# SMS Alerts (Twilio)
SMS_ENABLED=true
TWILIO_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM=+1234567890
ALERT_PHONE=+1234567890

# Slack Alerts
SLACK_ENABLED=true
SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

### Alert Thresholds

Edit `backend/app/anomalies.py` to adjust safety thresholds:

```python
THRESHOLDS = {
    'temp': {'min': 0, 'max': 30, 'critical_max': 35},
    'flow': {'min': 100, 'max': 5000, 'critical_min': 50},
    'turbidity': {'min': 0, 'max': 100, 'critical_max': 200},
}
```

## 🔄 CI/CD Pipelines

### Automated Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| **CI** | PR/Push | Lint, test, and build verification |
| **Docker Publish** | Push to main | Build and push images to GHCR |
| **Security Scan** | Schedule/PR | Vulnerability scanning with Trivy, Snyk, GitLeaks |
| **Deploy** | Tag/Manual | Deploy to production server |
| **Dependabot** | Schedule | Automated dependency updates |

### GitHub Secrets Required for Deployment

Set these in your GitHub repository Settings > Secrets and variables > Actions:

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Production server IP/hostname |
| `DEPLOY_USER` | SSH username for deployment |
| `SSH_PRIVATE_KEY` | SSH private key for deployment |
| `DB_PASSWORD` | Production database password |
| `SMTP_USER` | Email SMTP username |
| `SMTP_PASS` | Email SMTP password |
| `TWILIO_SID` | Twilio Account SID |
| `TWILIO_TOKEN` | Twilio Auth Token |
| `SLACK_WEBHOOK` | Slack webhook URL |

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status and info |
| GET | `/health` | Health check |
| GET | `/api/stations` | List all stations |
| GET | `/api/latest` | Latest readings from all stations |
| GET | `/api/historical/{station}` | Historical data for a station |
| GET | `/api/stats/{station}` | Statistical summary |

### Anomaly Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/anomalies` | List detected anomalies |
| POST | `/api/anomalies/detect` | Manual anomaly detection |
| POST | `/api/alerts/test` | Send test alert |
| GET | `/api/alerts/config` | Alert configuration status |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Consolidated dashboard data |

## 🔬 Anomaly Detection

The system uses a hybrid approach:

1. **Statistical Thresholds** - Hard limits for critical values
2. **Isolation Forest ML** - Unsupervised learning for pattern detection
3. **Time-series Analysis** - Trend and seasonality detection

Anomalies are classified by severity:
- 🔴 **Critical** - Immediate action required
- 🟠 **High** - Significant deviation
- 🟡 **Medium** - Moderate deviation
- 🔵 **Low** - Minor deviation

## 📊 Monitored Stations

| Station | Location | Parameters |
|---------|----------|------------|
| Newburgh | Hudson Valley | Temp, Flow, Turbidity, Salinity, DO, pH |
| Beacon | Hudson Valley | Temp, Flow, Turbidity, Salinity, DO, pH |
| West Point | Hudson Valley | Temp, Flow, Turbidity, Salinity, DO, pH |
| Poughkeepsie | Hudson Valley | Temp, Flow, Turbidity, Salinity, DO, pH |
| Albany | Capital Region | Temp, Flow, Turbidity |

## 🗄️ Database Backup & Restore

### Automated Backup

```bash
# Create backup (compressed)
./scripts/backup.sh ./backups

# Backup runs daily via cron (add to crontab)
0 2 * * * /path/to/hrecos-dashboard/scripts/backup.sh
```

### Restore from Backup

```bash
# Restore database
gunzip < backups/hrecos_backup_20240101_120000.sql.gz | \
  docker compose exec -T db psql -U postgres hrecos
```

## 📝 Data Retention

- **Raw readings**: 90 days
- **Anomaly logs**: 90 days
- **Daily backups**: 7 days
- **Weekly backups**: 4 weeks
- **Monthly backups**: 12 months

## 🌐 HRECOS Data Source

This dashboard integrates with the official HRECOS network:

- **Website**: https://hrecos.org
- **Data Access**: Real-time API (or mock data for development)
- **Update Frequency**: Every 15 minutes
- **Coverage**: Hudson River Estuary environmental conditions

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check database status
docker compose logs db

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### Alert Not Working

1. Check environment variables are set correctly
2. Verify alert configuration: `GET /api/alerts/config`
3. Send test alert: `POST /api/alerts/test`
4. Check backend logs: `docker compose logs backend`

### API Not Responding

```bash
# Restart backend
docker compose restart backend

# Check logs
docker compose logs -f backend
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

### Pull Request Checklist

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally
- [ ] Docker build is successful
- [ ] Documentation is updated
- [ ] Commit messages are descriptive

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/bass/hrecos-dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bass/hrecos-dashboard/discussions)
- **Email**: support@hrecos-dashboard.local

## 🙏 Acknowledgments

- [HRECOS](https://hrecos.org) for providing environmental data
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [TimescaleDB](https://www.timescale.com/) for time-series data storage

---

Built with ❤️ for the Hudson River community.

[![Deploy to Production](https://img.shields.io/badge/Deploy-Production-success?style=for-the-badge&logo=github-actions)](https://github.com/bass/hrecos-dashboard/actions/workflows/deploy.yml)
