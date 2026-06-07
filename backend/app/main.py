from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, engine
from app.models import Base, HRECOSReading, AnomalyLog
from app.hr_data import (
    STATIONS, REGIONS, FOCUS_STATIONS,
    fetch_all_stations, fetch_historical_data, stations_for_region,
)
from app.tides import TIDE_STATIONS, get_tide_station_key
from app.tasks import start_scheduler, stop_scheduler
from app.anomalies import AnomalyDetector
from app.alerts import alert_manager
from app.tides import get_tide_predictions, get_current_tide

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting HRECOS Dashboard...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    
    # Start the scheduler
    start_scheduler()
    print("✅ Scheduler started")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down HRECOS Dashboard...")
    stop_scheduler()
    await engine.dispose()
    print("✅ Cleanup complete")

app = FastAPI(
    title="HRECOS Dashboard API",
    description="Real-time environmental monitoring for the Hudson River",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "HRECOS Dashboard API",
        "version": "1.0.0",
        "status": "operational",
        "stations": list(STATIONS.keys()),
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "stations_configured": len(STATIONS)
    }

# ============================================================================
# Data Retrieval Endpoints
# ============================================================================

@app.get("/api/stations")
async def get_stations(region: Optional[str] = Query(None, description="Filter: cornwall_on_hudson (alias: cornwall)")):
    """Get list of configured monitoring stations"""
    if region and region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    pool = stations_for_region(region) if region else {k: STATIONS[k] for k in FOCUS_STATIONS if k in STATIONS}
    return {
        "region": region,
        "regions": REGIONS,
        "stations": [
            {
                "key": key,
                "name": config["name"],
                "id": config["id"],
                "region": config.get("region"),
                "live": config.get("live", False),
                "location": {"lat": config["lat"], "lon": config["lon"]},
                "parameters": config["params"],
                "note": config.get("note"),
            }
            for key, config in pool.items()
        ],
    }

@app.get("/api/latest")
async def get_latest_readings(
    station: Optional[str] = Query(None, description="Filter by station key"),
    region: Optional[str] = Query(None, description="Filter: cornwall_on_hudson (alias: cornwall)"),
):
    """Get latest readings from focus stations or a specific station"""
    if region and region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    if station and station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
    
    try:
        readings = await fetch_all_stations(region=region)
        
        if station:
            return {"station": station, "data": readings.get(station)}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "region": region,
            "readings": readings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@app.get("/api/data")
async def get_data(
    station: Optional[str] = Query(None, description="Filter by station key"),
    region: Optional[str] = Query(None, description="Filter: cornwall_on_hudson (alias: cornwall)"),
):
    """Alias for /api/latest — used by HRECOS RiverWatch Android app"""
    return await get_latest_readings(station=station, region=region)


@app.get("/api/historical/{station}")
async def get_historical_data(
    station: str,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db)
):
    """Get historical data for a specific station"""
    if station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
    
    try:
        # Try to get from database first
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        result = await db.execute(
            select(HRECOSReading)
            .where(HRECOSReading.station == station)
            .where(HRECOSReading.timestamp >= cutoff)
            .order_by(HRECOSReading.timestamp.desc())
        )
        readings = result.scalars().all()
        
        if readings:
            return {
                "station": station,
                "hours": hours,
                "count": len(readings),
                "data": [
                    {
                        "timestamp": r.timestamp.isoformat(),
                        "temp": r.temp,
                        "flow": r.flow,
                        "turbidity": r.turbidity,
                        "salinity": r.salinity,
                        "dissolved_oxygen": r.dissolved_oxygen,
                        "ph": r.ph
                    }
                    for r in readings
                ]
            }
        
        # Fallback to mock data
        mock_data = fetch_historical_data(station, hours)
        return {
            "station": station,
            "hours": hours,
            "count": len(mock_data),
            "data": mock_data,
            "note": "Using mock data - database empty"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")

# ============================================================================
# Statistics & Analytics Endpoints
# ============================================================================

@app.get("/api/stats/{station}")
async def get_station_stats(
    station: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get statistical summary for a station"""
    if station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
    
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Build aggregation query
        metrics = [
            func.count().label('count'),
            func.avg(HRECOSReading.temp).label('avg_temp'),
            func.min(HRECOSReading.temp).label('min_temp'),
            func.max(HRECOSReading.temp).label('max_temp'),
            func.avg(HRECOSReading.flow).label('avg_flow'),
            func.min(HRECOSReading.flow).label('min_flow'),
            func.max(HRECOSReading.flow).label('max_flow'),
            func.avg(HRECOSReading.turbidity).label('avg_turbidity'),
        ]
        
        result = await db.execute(
            select(*metrics)
            .where(HRECOSReading.station == station)
            .where(HRECOSReading.timestamp >= cutoff)
        )
        
        row = result.one()
        
        return {
            "station": station,
            "period_hours": hours,
            "readings_count": row.count,
            "temperature": {
                "avg": round(row.avg_temp, 2) if row.avg_temp else None,
                "min": round(row.min_temp, 2) if row.min_temp else None,
                "max": round(row.max_temp, 2) if row.max_temp else None,
            },
            "flow": {
                "avg": round(row.avg_flow, 2) if row.avg_flow else None,
                "min": round(row.min_flow, 2) if row.min_flow else None,
                "max": round(row.max_flow, 2) if row.max_flow else None,
            },
            "turbidity": {
                "avg": round(row.avg_turbidity, 2) if row.avg_turbidity else None,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")

# ============================================================================
# Anomaly Detection Endpoints
# ============================================================================

@app.get("/api/anomalies")
async def get_anomalies(
    station: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get detected anomalies with optional filtering"""
    try:
        query = select(AnomalyLog).order_by(desc(AnomalyLog.timestamp))
        
        if station:
            query = query.where(AnomalyLog.station == station)
        if severity:
            query = query.where(AnomalyLog.severity == severity)
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        anomalies = result.scalars().all()
        
        return {
            "count": len(anomalies),
            "anomalies": [
                {
                    "id": a.id,
                    "station": a.station,
                    "timestamp": a.timestamp.isoformat(),
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "value": a.value,
                    "expected_range": a.expected_range,
                    "alert_sent": a.alert_sent
                }
                for a in anomalies
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching anomalies: {str(e)}")

@app.post("/api/anomalies/detect")
async def run_anomaly_detection(station: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger anomaly detection for a station"""
    if station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
    
    try:
        # Get recent data
        cutoff = datetime.utcnow() - timedelta(hours=48)
        result = await db.execute(
            select(HRECOSReading)
            .where(HRECOSReading.station == station)
            .where(HRECOSReading.timestamp >= cutoff)
            .order_by(HRECOSReading.timestamp)
        )
        readings = result.scalars().all()
        
        if len(readings) < 10:
            raise HTTPException(status_code=400, detail="Insufficient data for anomaly detection (need at least 10 readings)")
        
        # Run detection
        try:
            import pandas as pd
        except ImportError:
            raise HTTPException(status_code=503, detail="ML anomaly detection not available in mobile mode. Install pandas and scikit-learn.")
        df = pd.DataFrame([
            {
                "timestamp": r.timestamp,
                "temp": r.temp,
                "flow": r.flow,
                "turbidity": r.turbidity,
                "salinity": r.salinity,
                "dissolved_oxygen": r.dissolved_oxygen,
                "ph": r.ph
            }
            for r in readings
        ])
        
        detector = AnomalyDetector()
        detector.fit(df)
        df = detector.detect(df)
        anomalies = detector.get_anomaly_details(df, station)
        
        return {
            "station": station,
            "readings_analyzed": len(readings),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in anomaly detection: {str(e)}")

# ============================================================================
# Alert Management Endpoints
# ============================================================================

@app.post("/api/alerts/test")
async def send_test_alert(channel: str = "email"):
    """Send a test alert to verify configuration"""
    test_anomaly = {
        "id": f"test_{datetime.utcnow().isoformat()}",
        "station": "test-station",
        "timestamp": datetime.utcnow(),
        "anomaly_type": "test",
        "severity": "medium",
        "value": 25.5,
        "expected_range": "20-30",
        "score": 2.5
    }
    
    try:
        await alert_manager.send_alert(test_anomaly, channels=[channel])
        return {"status": "success", "message": f"Test alert sent via {channel}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")

@app.get("/api/alerts/config")
async def get_alert_config():
    """Get current alert configuration status"""
    return {
        "email": {
            "enabled": alert_manager.email_enabled,
            "configured": bool(alert_manager.smtp_user and alert_manager.smtp_pass)
        },
        "sms": {
            "enabled": alert_manager.sms_enabled,
            "configured": bool(alert_manager.twilio_sid and alert_manager.twilio_token)
        },
        "slack": {
            "enabled": alert_manager.slack_enabled,
            "configured": bool(alert_manager.slack_webhook)
        }
    }

# ============================================================================
# Dashboard Data Endpoint
# ============================================================================

@app.get("/api/tides")
async def get_tides(
    hours: int = Query(48, ge=1, le=168),
    region: str = Query("cornwall_on_hudson", description="cornwall_on_hudson (alias: cornwall)"),
):
    """Get tide predictions for Cornwall-on-Hudson (Newburgh station)"""
    if region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    try:
        tide_key = get_tide_station_key(region)
        tide_cfg = TIDE_STATIONS[tide_key]
        tides = get_tide_predictions(hours=hours, region=region)
        current = get_current_tide(region=region)
        return {
            "region": region,
            "location": REGIONS[region]["name"],
            "station": tide_cfg["id"],
            "station_name": tide_cfg["name"],
            "station_key": tide_key,
            "hours": hours,
            "current": {
                **current,
                "next_time": current["next_time"].isoformat() if current.get("next_time") else None,
            },
            "predictions": [
                {
                    "time": t["time"].isoformat(),
                    "height": t["height"],
                    "type": t["type"],
                }
                for t in tides[:48]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tides: {str(e)}")


@app.get("/api/tides/current")
async def get_current_tide_info(region: str = Query("cornwall_on_hudson", description="cornwall_on_hudson")):
    """Get current tide status for Cornwall-on-Hudson (Newburgh)"""
    if region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    try:
        current = get_current_tide(region=region)
        if current.get("next_time"):
            current = {**current, "next_time": current["next_time"].isoformat()}
        return current
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching current tide: {str(e)}")


@app.get("/api/history")
async def get_history(
    hours: int = Query(24, ge=1, le=720),
    region: Optional[str] = Query(None, description="cornwall_on_hudson (alias: cornwall)"),
):
    """Aggregated historical data for Cornwall-on-Hudson corridor"""
    if region and region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    try:
        pool = stations_for_region(region) if region else {k: STATIONS[k] for k in FOCUS_STATIONS if k in STATIONS}
        out = {}
        for key in pool:
            rows = fetch_historical_data(key, hours)
            out[key] = rows
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@app.get("/api/dashboard")
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    """Get consolidated data for the main dashboard"""
    try:
        # Latest readings
        latest = await fetch_all_stations()
        
        # Recent anomalies count
        day_ago = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            select(func.count()).select_from(AnomalyLog)
            .where(AnomalyLog.timestamp >= day_ago)
        )
        recent_anomalies = result.scalar()
        
        # Alert status
        result = await db.execute(
            select(func.count()).select_from(AnomalyLog)
            .where(AnomalyLog.alert_sent == 'pending')
        )
        pending_alerts = result.scalar()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "regions": REGIONS,
            "stations_online": len(FOCUS_STATIONS),
            "latest_readings": latest,
            "alerts": {
                "recent_24h": recent_anomalies,
                "pending": pending_alerts
            },
            "system_status": "operational"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
