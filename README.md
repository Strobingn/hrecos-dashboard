# 🌊 HRECOS Dashboard

Real-time environmental monitoring dashboard for the **Hudson River Environmental Conditions Observing System (HRECOS)**.

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
├── docker-compose.yml # Infrastructure orchestration
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Deploy

```bash
# Clone the repository
git clone <repo-url>
cd hrecos-dashboard

# Copy environment template
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

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Email Alerts (Gmail SMTP)
EMAIL_ENABLED=true
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
ALERT_EMAIL=recipient@example.com

# SMS Alerts (Twilio)
SMS_ENABLED=true
TWILIO_SID=your-account-sid
TWILIO_TOKEN=your-auth-token
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

## 🛠️ Development

### Local Development (without Docker)

```bash
# Setup Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database (requires PostgreSQL 14+)
createdb hrecos

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload

# Frontend (serve with any static server)
cd ../frontend
python -m http.server 8080
```

### Testing

```bash
# Test alert configuration
curl -X POST http://localhost:8000/api/alerts/test?channel=email

# Manual anomaly detection
curl -X POST http://localhost:8000/api/anomalies/detect?station=newburgh

# Get latest readings
curl http://localhost:8000/api/latest
```

## 📝 Data Retention

- **Raw readings**: 90 days
- **Anomaly logs**: 90 days
- **Aggregation**: Configurable in `tasks.py`

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

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📞 Support

For issues and feature requests, please open a GitHub issue.

---

Built with ❤️ for the Hudson River community.
