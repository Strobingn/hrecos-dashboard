from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class HRECOSReading(Base):
    __tablename__ = "hrecos_readings"
    
    station = Column(String(50), primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    temp = Column(Float, nullable=True)
    flow = Column(Float, nullable=True)
    turbidity = Column(Float, nullable=True)
    salinity = Column(Float, nullable=True)
    dissolved_oxygen = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    
    # Create hypertable index for TimescaleDB optimization
    __table_args__ = (
        Index('idx_station_time', 'station', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
    )

class AnomalyLog(Base):
    __tablename__ = "anomaly_logs"
    
    id = Column(String(100), primary_key=True)  # station_timestamp format
    station = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    anomaly_type = Column(String(50), nullable=False)  # 'temp', 'flow', 'turbidity', etc.
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    value = Column(Float, nullable=False)
    expected_range = Column(String(100), nullable=True)  # "min-max" format
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    alert_sent = Column(String(10), default='pending')  # 'pending', 'sent', 'failed'

class AlertConfig(Base):
    __tablename__ = "alert_configs"
    
    id = Column(String(50), primary_key=True)
    station = Column(String(50), nullable=True)  # NULL means all stations
    alert_type = Column(String(20), nullable=False)  # 'email', 'sms', 'webhook'
    target = Column(String(255), nullable=False)  # email, phone, or webhook URL
    enabled = Column(String(5), default='true')
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
