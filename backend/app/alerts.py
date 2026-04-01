import os
import smtplib
import asyncio
from email.message import EmailMessage
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertManager:
    """Manages email and SMS alerts for HRECOS anomalies"""
    
    def __init__(self):
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.sms_enabled = os.getenv("SMS_ENABLED", "false").lower() == "true"
        self.slack_enabled = os.getenv("SLACK_ENABLED", "false").lower() == "true"
        
        # Email configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("FROM_EMAIL", "alerts@hrecos-dashboard.local")
        
        # SMS configuration (Twilio)
        self.twilio_sid = os.getenv("TWILIO_SID", "")
        self.twilio_token = os.getenv("TWILIO_TOKEN", "")
        self.twilio_from = os.getenv("TWILIO_FROM", "")
        
        # Slack configuration
        self.slack_webhook = os.getenv("SLACK_WEBHOOK", "")
        
    async def send_alert(self, anomaly: Dict, channels: Optional[List[str]] = None):
        """Send alert through configured channels"""
        if channels is None:
            channels = ['email'] if self.email_enabled else []
            if self.sms_enabled:
                channels.append('sms')
            if self.slack_enabled:
                channels.append('slack')
        
        tasks = []
        
        if 'email' in channels and self.email_enabled:
            tasks.append(self._send_email_alert(anomaly))
        if 'sms' in channels and self.sms_enabled:
            tasks.append(self._send_sms_alert(anomaly))
        if 'slack' in channels and self.slack_enabled:
            tasks.append(self._send_slack_alert(anomaly))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_email_alert(self, anomaly: Dict):
        """Send email alert"""
        try:
            msg = EmailMessage()
            
            subject = f"🚨 HRECOS Alert: {anomaly['severity'].upper()} {anomaly['anomaly_type']} at {anomaly['station']}"
            
            body = f"""
HRECOS Environmental Monitoring Alert
{'='*50}

Station: {anomaly['station']}
Timestamp: {anomaly['timestamp']}
Severity: {anomaly['severity'].upper()}
Parameter: {anomaly['anomaly_type']}

Current Value: {anomaly['value']:.2f}
Expected Range: {anomaly.get('expected_range', 'N/A')}
Anomaly Score: {anomaly.get('score', 'N/A')}

This is an automated alert from the HRECOS Dashboard monitoring system.
Please investigate the environmental conditions at the affected station.

---
HRECOS Dashboard | Hudson River Environmental Conditions Observing System
            """
            
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = os.getenv("ALERT_EMAIL", "admin@example.com")
            
            # Run blocking SMTP operation in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)
            
            logger.info(f"Email alert sent for {anomaly['station']}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_smtp(self, msg: EmailMessage):
        """Synchronous SMTP sending"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
    
    async def _send_sms_alert(self, anomaly: Dict):
        """Send SMS alert via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_sid, self.twilio_token)
            
            body = f"🚨 HRECOS: {anomaly['severity'].upper()} {anomaly['anomaly_type']} at {anomaly['station']}: {anomaly['value']:.2f} (Expected: {anomaly.get('expected_range', 'N/A')})"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    body=body[:160],  # SMS limit
                    from_=self.twilio_from,
                    to=os.getenv("ALERT_PHONE", "+1234567890")
                )
            )
            
            logger.info(f"SMS alert sent for {anomaly['station']}")
            
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
    
    async def _send_slack_alert(self, anomaly: Dict):
        """Send Slack webhook alert"""
        try:
            import httpx
            
            color = {
                'low': '#36a64f',
                'medium': '#daa520',
                'high': '#ff4500',
                'critical': '#dc143c'
            }.get(anomaly['severity'], '#808080')
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"🚨 HRECOS Alert: {anomaly['severity'].upper()} {anomaly['anomaly_type']}",
                    "fields": [
                        {"title": "Station", "value": anomaly['station'], "short": True},
                        {"title": "Parameter", "value": anomaly['anomaly_type'], "short": True},
                        {"title": "Current Value", "value": f"{anomaly['value']:.2f}", "short": True},
                        {"title": "Expected Range", "value": anomaly.get('expected_range', 'N/A'), "short": True},
                        {"title": "Timestamp", "value": str(anomaly['timestamp']), "short": False}
                    ],
                    "footer": "HRECOS Dashboard",
                    "ts": datetime.now().timestamp()
                }]
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(self.slack_webhook, json=payload)
            
            logger.info(f"Slack alert sent for {anomaly['station']}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def format_alert_message(self, anomaly: Dict) -> str:
        """Format alert message for display"""
        return f"""
┌─────────────────────────────────────────┐
│  🚨 HRECOS ENVIRONMENTAL ALERT          │
├─────────────────────────────────────────┤
│  Station:    {anomaly['station']:<25}│
│  Parameter:  {anomaly['anomaly_type']:<25}│
│  Severity:   {anomaly['severity'].upper():<25}│
│  Value:      {anomaly['value']:<25.2f}│
│  Expected:   {anomaly.get('expected_range', 'N/A'):<25}│
│  Time:       {str(anomaly['timestamp'])[:25]:<25}│
└─────────────────────────────────────────┘
        """

# Global alert manager instance
alert_manager = AlertManager()

async def send_bulk_alerts(anomalies: List[Dict]):
    """Send multiple alerts efficiently"""
    if not anomalies:
        return
    
    tasks = [alert_manager.send_alert(anomaly) for anomaly in anomalies]
    await asyncio.gather(*tasks, return_exceptions=True)
