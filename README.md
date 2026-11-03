# 🌊 HRECOS Dashboard

Real-time environmental monitoring dashboard for the **Hudson River Environmental Conditions Observing System (HRECOS)**.

[![CI](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/docker-publish.yml)
[![Security Scan](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/security-scan.yml/badge.svg)](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/security-scan.yml)
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
├── backend/              # FastAPI service (SQLAlchemy async + APScheduler)
│   ├── app/              # entry point: app/main.py
│   └── tests/            # pytest suite (runs in CI)
├── frontend/             # Served web dashboard (single file, Chart.js + Leaflet)
│   ├── index.html
│   └── Dockerfile
├── mobile/               # Expo / React Native Android app ("RiverWatch")
├── contracts/            # JSON Schemas for the fish-acoustic network (not wired up yet)
├── supabase/             # Supabase migration + seed for that schema
├── init-scripts/         # TimescaleDB init SQL (extension only; tables come from SQLAlchemy)
├── docs/                 # Design notes (see docs/fish-network.md)
├── scripts/              # setup / backup / deploy helpers
├── legacy/               # Superseded PWA + Capacitor shell — reference only
├── docker-compose.yml        # Development stack (bind mounts, --reload)
├── docker-compose.local.yml  # Dev stack with plain PostgreSQL instead of TimescaleDB
├── docker-compose.prod.yml   # Production stack, standalone (images pulled from GHCR)
└── Makefile
```

### Which frontend is which?

- `frontend/index.html` — the web dashboard served by nginx. It calls `/api/` on
  the same origin by default. Set `window.HRECOS_API_BASE` to point at another
  backend, or `window.HRECOS_DISABLE_API = true` for a pure offline demo. The
  badge above the map always reads **Live API** or **SIMULATED DATA** — the
  dashboard never presents generated numbers as live.
- `mobile/` — the Expo Android app and the primary mobile client.
- `legacy/cornwall-pwa/` — an old hard-coded PWA, kept for reference only.

### Data sources

The backend pulls from public observation services directly — there is no
dependency on a hrecos.org API:

| Source | Used for |
|--------|----------|
| USGS NWIS | water temperature, flow, turbidity, dissolved oxygen, pH |
| NOAA CO-OPS | tide predictions and water temperature (Newburgh 8518935, Turkey Point) |
| NOAA NDBC | air temperature, wind, pressure (Norrie Point NPXN6) |

Values are converted to imperial units (°F, mph, inHg, ft³/s) at ingestion, so
every API response is imperial. The mobile app converts to metric on display.

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Deploy

```bash
# Clone the repository
git clone https://github.com/Strobingn/hrecos-dashboard.git
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

# Frontend (serve with any static server, or use the Docker stack)
cd ../frontend
python -m http.server 8080
```

### Testing

```bash
cd backend
pip install pytest
python -m pytest tests -v
```

The suite uses a throwaway SQLite database and monkeypatches the external data
fetchers, so it runs offline. CI runs it on every push and pull request.

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
    'temp': {'min': 32, 'max': 86, 'critical_max': 95},   # °F
    'flow': {'min': 100, 'max': 5000, 'critical_min': 50},
    'turbidity': {'min': 0, 'max': 100, 'critical_max': 200},
    'dissolved_oxygen': {'min': 4, 'max': 15, 'critical_min': 2},
    'ph': {'min': 6.0, 'max': 9.0},
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
| `DB_PASSWORD` | Production database password (required) |
| `SECRET_KEY` | Application secret, 32+ characters (required) |
| `HRECOS_CORS_ORIGINS` | Comma-separated allowed browser origins |
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
| GET | `/api/data` | Alias for `/api/latest` (used by the mobile app) |
| GET | `/api/history` | Aggregated history for the focus station set |
| GET | `/api/historical/{station}` | Historical data for a station |
| GET | `/api/stats/{station}` | Statistical summary |
| GET | `/api/tides` | NOAA tide predictions (Newburgh 8518935) |
| GET | `/api/tides/current` | Current tide height and next event |

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

The default focus set (`FOCUS_STATIONS` in `backend/app/hr_data.py`) is:

| Station | Source | Parameters |
|---------|--------|------------|
| Norrie Point (NPXN6) | NOAA NDBC | air temperature, wind, pressure |
| Turkey Point | NOAA CO-OPS | water temperature, conductance |
| Newburgh (8518935) | NOAA CO-OPS | tide predictions |
| West Point | USGS | water quality (historical / decommissioned site) |

The registry also contains additional Hudson stations that can be queried with
`?region=`; see `STATIONS` in `backend/app/hr_data.py`.

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

## 🌐 Data Sources

This dashboard reads public observation data directly. No API key is required.

- **USGS NWIS** — https://waterservices.usgs.gov
- **NOAA CO-OPS** — https://tidesandcurrents.noaa.gov
- **NOAA NDBC** — https://www.ndbc.noaa.gov

Each fetcher falls back to generated sample data when a source is unreachable;
API responses flag which fields are real. The web dashboard shows a prominent
**SIMULATED DATA** badge whenever it cannot reach the backend.

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

- **Issues**: [GitHub Issues](https://github.com/Strobingn/hrecos-dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Strobingn/hrecos-dashboard/discussions)
- **Email**: support@hrecos-dashboard.local

## 🙏 Acknowledgments

- [HRECOS](https://hrecos.org) for providing environmental data
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [TimescaleDB](https://www.timescale.com/) for time-series data storage

---

Built with ❤️ for the Hudson River community.

[![Deploy to Production](https://img.shields.io/badge/Deploy-Production-success?style=for-the-badge&logo=github-actions)](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/deploy.yml)
