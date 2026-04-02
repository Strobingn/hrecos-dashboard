"""
Tide data for Cornwall, NY (Hudson River)
Uses NOAA Tides & Currents API
Station: 8518490 (Newburgh) - closest to Cornwall
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# NOAA Station IDs near Cornwall, NY
# 8518490 = Newburgh (closest, ~3 miles south)
# 8518951 = West Point (~10 miles north)
NOAA_STATION = "8518490"  # Newburgh

NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def get_tide_predictions(hours: int = 48) -> List[Dict]:
    """Get tide predictions for the next N hours"""
    now = datetime.utcnow()
    begin_date = now.strftime("%Y%m%d %H:%M")
    end_date = (now + timedelta(hours=hours)).strftime("%Y%m%d %H:%M")
    
    params = {
        "station": NOAA_STATION,
        "product": "predictions",
        "begin_date": begin_date,
        "end_date": end_date,
        "datum": "mllw",  # Mean Lower Low Water
        "units": "english",
        "time_zone": "lst_ldt",  # Local standard/daylight time
        "format": "json",
    }
    
    try:
        response = requests.get(NOAA_API_BASE, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            predictions = data.get("predictions", [])
            return [
                {
                    "time": datetime.strptime(p["t"], "%Y-%m-%d %H:%M"),
                    "height": float(p["v"]),  # feet
                    "type": "high" if i > 0 and float(p["v"]) > float(predictions[i-1]["v"]) else "low" if i > 0 else "unknown"
                }
                for i, p in enumerate(predictions)
            ]
    except Exception as e:
        print(f"Tide fetch error: {e}")
    
    # Fallback: generate synthetic tide data
    return generate_synthetic_tides(hours)


def generate_synthetic_tides(hours: int = 48) -> List[Dict]:
    """Generate synthetic tide data when API fails"""
    import math
    
    tides = []
    now = datetime.utcnow()
    
    # Hudson River has mixed tides, approximately every 6 hours
    for i in range(hours * 2):  # 2 predictions per hour
        t = now + timedelta(minutes=i * 30)
        # Simulate mixed tide pattern
        height = 2.5 + 2.0 * math.sin(i * 0.52) + 0.5 * math.sin(i * 1.04)
        
        # Determine high/low
        prev_height = tides[-1]["height"] if tides else height
        tide_type = "high" if height > prev_height else "low"
        
        tides.append({
            "time": t,
            "height": round(height, 2),
            "type": tide_type
        })
    
    return tides


def get_next_tide_change() -> Optional[datetime]:
    """Get the time of the next tide change (high or low)"""
    tides = get_tide_predictions(hours=12)
    now = datetime.utcnow()
    
    for tide in tides:
        if tide["time"] > now:
            return tide["time"]
    
    return None


def get_current_tide() -> Dict:
    """Get current tide information"""
    tides = get_tide_predictions(hours=6)
    now = datetime.utcnow()
    
    # Find current tide
    current = tides[0] if tides else {"height": 2.5, "type": "unknown", "time": now}
    
    for i, tide in enumerate(tides):
        if tide["time"] > now:
            current = tides[i-1] if i > 0 else tide
            break
    
    # Find next tide
    next_tide = None
    for tide in tides:
        if tide["time"] > now:
            next_tide = tide
            break
    
    return {
        "current_height": current["height"],
        "current_type": current["type"],
        "next_time": next_tide["time"] if next_tide else None,
        "next_type": next_tide["type"] if next_tide else None,
        "next_height": next_tide["height"] if next_tide else None,
    }


def should_poll_data() -> bool:
    """Check if we should poll data (at tide changes or every hour)"""
    current = get_current_tide()
    now = datetime.utcnow()
    
    if current["next_time"]:
        # Poll 30 minutes before and after tide change
        time_to_tide = (current["next_time"] - now).total_seconds() / 60
        if -30 <= time_to_tide <= 30:
            return True
    
    # Also poll every hour as backup
    return now.minute < 10
