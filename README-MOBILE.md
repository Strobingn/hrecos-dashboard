# Running HRECOS Dashboard on Mobile / Without Docker

No Docker, no PostgreSQL, no external services required.

## Requirements
- Python 3.10 or higher
- pip3
- ~150MB disk space for dependencies

## Quick Start

```bash
git clone https://github.com/Strobingn/hrecos-dashboard
cd hrecos-dashboard
./run_mobile.sh
```

Then open **http://localhost:8080** in your browser.

## What runs
| Component | How |
|---|---|
| Backend API | FastAPI + uvicorn on port 8000 |
| Database | SQLite (`hrecos.db`) — no server needed |
| Frontend | Python's built-in HTTP server on port 8080 |
| Alerts | Disabled by default |

## Data Sources (live, no API keys needed)
| Station | Source | River Mile | Live |
|---|---|---|---|
| Albany | USGS 01359139 | RM 143 | ✅ |
| Schodack Landing | USGS 0135980207 | RM 120 | ✅ |
| Coxsackie | NOAA 8518979 | RM 108 | ✅ |
| Turkey Point (NERRS) | NOAA 8518962 | RM 84 | ✅ |
| Norrie Point (HRNERR) | NDBC NPXN6 | RM 88 | ✅ met only |

All temperatures in °F, wind in mph, pressure in inHg.

## Monitoring Gap
No active water quality sensors exist on the Hudson River main stem
between Piermont (RM 25) and Turkey Point (RM 84) — a 59-mile gap.
This gap encompasses the proposed hydrophone deployment corridor
(Storm King RM 55 → Kingston RM 90).

## To enable alerts
Copy `.env.example` to `.env` and fill in your credentials,
then re-run `./run_mobile.sh`.

## Dependencies (~150MB)
See `requirements-mobile.txt` — PostgreSQL driver (`psycopg2`, `asyncpg`)
and Twilio are excluded. Full production stack uses `requirements.txt`.
