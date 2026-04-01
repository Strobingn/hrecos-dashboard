import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from typing import Dict
import logging

from app.db import async_session
from app.models import HRECOSReading, AnomalyLog
from app.hr_data import STATIONS, fetch_station_sync
from app.anomalies import AnomalyDetector, check_thresholds
from app.alerts import alert_manager, send_bulk_alerts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HRECOSScheduler:
    """Manages scheduled data fetching and anomaly detection"""
    
    def __init__(self):
        self.scheduler = None
        self.detector = AnomalyDetector(contamination=0.05)
        self._data_buffer: Dict[str, list] = {name: [] for name in STATIONS.keys()}
        
    def start(self):
        """Start the scheduler with configured jobs"""
        self.scheduler = AsyncIOScheduler()
        
        # Data fetching job - every 10 minutes
        self.scheduler.add_job(
            self.fetch_and_save_all,
            trigger=IntervalTrigger(minutes=10),
            id='fetch_data',
            name='Fetch HRECOS Data',
            replace_existing=True
        )
        
        # Anomaly detection job - every 15 minutes
        self.scheduler.add_job(
            self.run_anomaly_detection,
            trigger=IntervalTrigger(minutes=15),
            id='detect_anomalies',
            name='Detect Anomalies',
            replace_existing=True
        )
        
        # Cleanup old data job - daily
        self.scheduler.add_job(
            self.cleanup_old_data,
            trigger=IntervalTrigger(days=1),
            id='cleanup_data',
            name='Cleanup Old Data',
            replace_existing=True
        )
        
        # Add listeners for job events
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        self.scheduler.start()
        logger.info("Scheduler started with jobs: fetch_data (10min), detect_anomalies (15min), cleanup_data (daily)")
        
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def _on_job_executed(self, event):
        """Handle job execution events"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} completed successfully")
    
    async def fetch_and_save_all(self):
        """Fetch data from all stations and save to database"""
        logger.info(f"[{datetime.utcnow()}] Fetching data from all stations...")
        
        for station_key, station_config in STATIONS.items():
            try:
                # Fetch data
                record = fetch_station_sync(station_key, station_config)
                
                if not record:
                    logger.warning(f"No data received for station {station_key}")
                    continue
                
                # Check for critical thresholds
                threshold_alerts = check_thresholds(record)
                if threshold_alerts:
                    for alert in threshold_alerts:
                        logger.warning(f"Threshold alert for {station_key}: {alert['message']}")
                
                # Save to database
                await self._save_reading(station_key, record)
                
                # Buffer data for anomaly detection
                self._data_buffer[station_key].append(record)
                # Keep only last 100 readings per station
                if len(self._data_buffer[station_key]) > 100:
                    self._data_buffer[station_key].pop(0)
                
                logger.info(f"Saved reading for {station_key}: temp={record.get('temp')}, flow={record.get('flow')}")
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing station {station_key}: {e}")
    
    async def _save_reading(self, station: str, record: Dict):
        """Save a reading to the database"""
        async with async_session() as session:
            try:
                reading = HRECOSReading(
                    station=station,
                    timestamp=record.get('timestamp', datetime.utcnow()),
                    temp=record.get('temp'),
                    flow=record.get('flow'),
                    turbidity=record.get('turbidity'),
                    salinity=record.get('salinity'),
                    dissolved_oxygen=record.get('dissolved_oxygen'),
                    ph=record.get('ph')
                )
                session.add(reading)
                await session.commit()
            except Exception as e:
                logger.error(f"Database error saving reading: {e}")
                await session.rollback()
    
    async def run_anomaly_detection(self):
        """Run anomaly detection on buffered data"""
        logger.info(f"[{datetime.utcnow()}] Running anomaly detection...")
        
        import pandas as pd
        
        all_anomalies = []
        
        for station, buffer in self._data_buffer.items():
            if len(buffer) < 10:
                logger.info(f"Insufficient data for {station} ({len(buffer)} readings), skipping...")
                continue
            
            try:
                # Convert to DataFrame
                df = pd.DataFrame(buffer)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Fit and detect
                self.detector.fit(df)
                df = self.detector.detect(df)
                
                # Get anomaly details
                anomalies = self.detector.get_anomaly_details(df, station)
                
                # Save anomalies to database
                for anomaly in anomalies:
                    await self._save_anomaly(anomaly)
                    all_anomalies.append(anomaly)
                
                if anomalies:
                    logger.warning(f"Detected {len(anomalies)} anomalies for {station}")
                else:
                    logger.info(f"No anomalies detected for {station}")
                    
            except Exception as e:
                logger.error(f"Error in anomaly detection for {station}: {e}")
        
        # Send alerts for all detected anomalies
        if all_anomalies:
            logger.info(f"Sending alerts for {len(all_anomalies)} anomalies...")
            await send_bulk_alerts(all_anomalies)
    
    async def _save_anomaly(self, anomaly: Dict):
        """Save an anomaly record to database"""
        async with async_session() as session:
            try:
                # Check if already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(AnomalyLog).where(AnomalyLog.id == anomaly['id'])
                )
                if result.scalar_one_or_none():
                    return  # Already exists
                
                log = AnomalyLog(
                    id=anomaly['id'],
                    station=anomaly['station'],
                    timestamp=anomaly['timestamp'],
                    anomaly_type=anomaly['anomaly_type'],
                    severity=anomaly['severity'],
                    value=anomaly['value'],
                    expected_range=anomaly.get('expected_range'),
                    alert_sent='pending'
                )
                session.add(log)
                await session.commit()
            except Exception as e:
                logger.error(f"Database error saving anomaly: {e}")
                await session.rollback()
    
    async def cleanup_old_data(self):
        """Remove data older than retention period"""
        from datetime import timedelta
        from sqlalchemy import delete
        
        retention_days = 90
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        async with async_session() as session:
            try:
                # Delete old readings
                stmt = delete(HRECOSReading).where(HRECOSReading.timestamp < cutoff_date)
                result = await session.execute(stmt)
                deleted_readings = result.rowcount
                
                # Delete old anomaly logs
                stmt = delete(AnomalyLog).where(AnomalyLog.timestamp < cutoff_date)
                result = await session.execute(stmt)
                deleted_anomalies = result.rowcount
                
                await session.commit()
                logger.info(f"Cleaned up {deleted_readings} old readings and {deleted_anomalies} old anomalies")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                await session.rollback()

# Global scheduler instance
scheduler = HRECOSScheduler()

def start_scheduler():
    """Start the global scheduler"""
    scheduler.start()

def stop_scheduler():
    """Stop the global scheduler"""
    scheduler.stop()
