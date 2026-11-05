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
| Piermont | HRECOS HPMNT | RM 25 | ✅ |
| West Point | HRECOS HWEST | RM 52 | ✅ |
| Poughkeepsie | HRECOS HPOUG | RM 75 | ✅ |
| Port of Albany | HRECOS HPORT | RM 142 | ✅ |
| Albany | USGS 01359139 | RM 143 | ✅ water temp only |
| Schodack Landing | HRECOS HSCHO | RM 120 | ❌ not live |
| Coxsackie | NOAA 8518979 | RM 108 | ✅ |
| Turkey Point (NERRS) | NOAA 8518962 | RM 84 | ✅ |
| Norrie Point (HRNERR) | NDBC NPXN6 | RM 88 | ✅ met only |

All temperatures in °F, wind in mph, pressure in inHg.

HRECOS water quality left USGS NWIS on April 1, 2026. Those stations now
come from the HRECOS export API (`nysm.hrecos.org`), which returns at most
60 days per request. The full station list is in `data/stations.json`.

## Monitoring Coverage
HRECOS West Point (RM 52) and Poughkeepsie (RM 75) report water quality
on the main stem around the proposed hydrophone deployment corridor
(Storm King RM 55 → Kingston RM 90). Cornwall itself has no public sensor.

## To enable alerts
Copy `.env.example` to `.env` and fill in your credentials,
then re-run `./run_mobile.sh`.

## Dependencies (~150MB)
See `requirements-mobile.txt` — PostgreSQL driver (`psycopg2`, `asyncpg`)
and Twilio are excluded. Full production stack uses `requirements.txt`.
