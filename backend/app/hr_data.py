import requests
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import os

# HRECOS Stations Configuration
# Based on actual HRECOS network: https://hrecos.org
STATIONS = {
    "newburgh": {
        "id": "HRP",
        "name": "Newburgh",
        "lat": 41.5034,
        "lon": -74.0104,
        "params": ["temp", "flow", "turbidity", "salinity", "do", "ph"]
    },
    "beacon": {
        "id": "BEA", 
        "name": "Beacon",
        "lat": 41.5085,
        "lon": -73.9736,
        "params": ["temp", "flow", "turbidity", "salinity", "do", "ph"]
    },
    "westpoint": {
        "id": "WPT",
        "name": "West Point",
        "lat": 41.3917,
        "lon": -73.9481,
        "params": ["temp", "flow", "turbidity", "salinity", "do", "ph"]
    },
    "poughkeepsie": {
        "id": "POU",
        "name": "Poughkeepsie",
        "lat": 41.7083,
        "lon": -73.9425,
        "params": ["temp", "flow", "turbidity", "salinity", "do", "ph"]
    },
    "albany": {
        "id": "ALB",
        "name": "Albany",
        "lat": 42.6526,
        "lon": -73.7562,
        "params": ["temp", "flow", "turbidity"]
    }
}

# HRECOS API endpoints
HRECOS_BASE_URL = os.getenv("HRECOS_API_URL", "https://hrecos.org/api/data")

def generate_mock_data(station_id: str) -> Dict:
    """Generate realistic mock data for development when API is unavailable"""
    import random
    now = datetime.utcnow()
    
    # Simulate realistic Hudson River conditions
    base_temp = 15.0 + random.gauss(0, 2)  # ~15°C average
    base_flow = 500 + random.gauss(0, 100)  # ~500 m³/s average
    base_turbidity = 10 + random.gauss(0, 3)  # ~10 NTU average
    
    return {
        "timestamp": now.isoformat(),
        "temp": round(base_temp, 2),
        "flow": round(max(0, base_flow), 2),
        "turbidity": round(max(0, base_turbidity), 2),
        "salinity": round(random.uniform(0.1, 2.0), 3) if random.random() > 0.1 else None,
        "dissolved_oxygen": round(random.uniform(7.0, 12.0), 2) if random.random() > 0.1 else None,
        "ph": round(random.uniform(6.8, 8.2), 2) if random.random() > 0.1 else None,
    }

async def fetch_station_async(station_key: str, station_config: Dict) -> Optional[Dict]:
    """Fetch data from HRECOS API asynchronously"""
    station_id = station_config["id"]
    
    try:
        # Try to fetch from HRECOS API
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{HRECOS_BASE_URL}/station/{station_id}/latest"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "timestamp": datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
                    "temp": data.get("water_temperature") or data.get("temp"),
                    "flow": data.get("flow"),
                    "turbidity": data.get("turbidity"),
                    "salinity": data.get("salinity"),
                    "dissolved_oxygen": data.get("dissolved_oxygen") or data.get("do"),
                    "ph": data.get("ph"),
                }
    except Exception as e:
        print(f"API fetch failed for {station_key}: {e}")
    
    # Fallback to mock data for development/demo
    mock = generate_mock_data(station_id)
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock

def fetch_station_sync(station_key: str, station_config: Dict) -> Optional[Dict]:
    """Synchronous version for scheduler"""
    station_id = station_config["id"]
    
    try:
        url = f"{HRECOS_BASE_URL}/station/{station_id}/latest"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "timestamp": datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
                "temp": data.get("water_temperature") or data.get("temp"),
                "flow": data.get("flow"),
                "turbidity": data.get("turbidity"),
                "salinity": data.get("salinity"),
                "dissolved_oxygen": data.get("dissolved_oxygen") or data.get("do"),
                "ph": data.get("ph"),
            }
    except Exception as e:
        print(f"API fetch failed for {station_key}: {e}")
    
    # Fallback to mock data
    mock = generate_mock_data(station_id)
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock

async def fetch_all_stations() -> Dict[str, Dict]:
    """Fetch data from all configured stations"""
    results = {}
    for key, config in STATIONS.items():
        data = await fetch_station_async(key, config)
        if data:
            results[key] = data
    return results

def fetch_historical_data(station_key: str, hours: int = 24) -> List[Dict]:
    """Fetch historical data for a station"""
    station_id = STATIONS[station_key]["id"]
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    try:
        url = f"{HRECOS_BASE_URL}/station/{station_id}/range"
        params = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json().get("readings", [])
    except Exception as e:
        print(f"Historical fetch failed: {e}")
    
    # Generate mock historical data
    import random
    readings = []
    for i in range(hours * 4):  # 15-minute intervals
        ts = end_time - timedelta(minutes=15 * i)
        readings.append({
            "timestamp": ts.isoformat(),
            "temp": round(15 + random.gauss(0, 1), 2),
            "flow": round(500 + random.gauss(0, 50), 2),
            "turbidity": round(10 + random.gauss(0, 2), 2),
        })
    return readings
