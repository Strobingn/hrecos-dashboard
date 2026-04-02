import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.db import get_db, engine, async_session
from app.models import Base, HRECOSReading, AnomalyLog
from app.hr_data import STATIONS, fetch_all_stations, fetch_historical_data
from app.tasks import start_scheduler, stop_scheduler, scheduler
from app.anomalies import AnomalyDetector, check_thresholds
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
async def get_stations():
    """Get list of all configured monitoring stations"""
    return {
        "stations": [
            {
                "key": key,
                "name": config["name"],
                "id": config["id"],
                "location": {"lat": config["lat"], "lon": config["lon"]},
                "parameters": config["params"]
            }
            for key, config in STATIONS.items()
        ]
    }

@app.get("/api/latest")
async def get_latest_readings(
    station: Optional[str] = Query(None, description="Filter by station key")
):
    """Get latest readings from all stations or a specific station"""
    if station and station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
    
    try:
        readings = await fetch_all_stations()
        
        if station:
            return {"station": station, "data": readings.get(station)}
        
        return {"timestamp": datetime.utcnow().isoformat(), "readings": readings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

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
async def get_tides(hours: int = Query(48, ge=1, le=168)):
    """Get tide predictions for Cornwall, NY area"""
    try:
        tides = get_tide_predictions(hours=hours)
        current = get_current_tide()
        return {
            "station": "8518490",  # Newburgh - closest to Cornwall
            "location": "Cornwall, NY Area",
            "hours": hours,
            "current": current,
            "predictions": [
                {
                    "time": t["time"].isoformat(),
                    "height": t["height"],
                    "type": t["type"]
                }
                for t in tides[:24]  # Limit to 24 points
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tides: {str(e)}")


@app.get("/api/tides/current")
async def get_current_tide_info():
    """Get current tide status for Cornwall, NY"""
    try:
        return get_current_tide()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching current tide: {str(e)}")


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
            "stations_online": len(STATIONS),
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
