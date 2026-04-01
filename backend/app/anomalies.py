import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class AnomalyDetector:
    """AI-powered anomaly detection for HRECOS environmental data"""
    
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Extract and scale features for anomaly detection"""
        feature_cols = ["temp", "flow", "turbidity"]
        if "salinity" in df.columns:
            feature_cols.append("salinity")
        if "dissolved_oxygen" in df.columns:
            feature_cols.append("dissolved_oxygen")
        if "ph" in df.columns:
            feature_cols.append("ph")
            
        # Fill NaN with column means
        features = df[feature_cols].copy()
        features = features.fillna(features.mean())
        
        # Add derived features for better detection
        if len(features) > 1:
            features['temp_change'] = features['temp'].diff().fillna(0)
            features['flow_change'] = features['flow'].diff().fillna(0)
        else:
            features['temp_change'] = 0
            features['flow_change'] = 0
            
        return features.values
    
    def fit(self, df: pd.DataFrame) -> 'AnomalyDetector':
        """Train the anomaly detection model"""
        if len(df) < 10:
            print("Insufficient data for training")
            return self
            
        features = self.prepare_features(df)
        scaled_features = self.scaler.fit_transform(features)
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto'
        )
        self.model.fit(scaled_features)
        self.is_fitted = True
        return self
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies in the dataset"""
        if not self.is_fitted or len(df) < 1:
            df['anomaly'] = 1  # Normal
            df['anomaly_score'] = 0.5
            return df
        
        features = self.prepare_features(df)
        scaled_features = self.scaler.transform(features)
        
        # Predict: -1 = anomaly, 1 = normal
        predictions = self.model.predict(scaled_features)
        scores = self.model.decision_function(scaled_features)
        
        df = df.copy()
        df['anomaly'] = predictions
        df['anomaly_score'] = scores
        
        return df
    
    def get_anomaly_details(self, df: pd.DataFrame, station: str) -> List[Dict]:
        """Extract detailed anomaly information for alerts"""
        anomalies = df[df['anomaly'] == -1].copy()
        details = []
        
        for idx, row in anomalies.iterrows():
            anomaly_types = []
            
            # Determine which parameters are anomalous
            if 'temp' in row and pd.notna(row['temp']):
                temp_zscore = abs((row['temp'] - df['temp'].mean()) / df['temp'].std()) if df['temp'].std() > 0 else 0
                if temp_zscore > 2:
                    anomaly_types.append(('temp', row['temp'], temp_zscore))
                    
            if 'flow' in row and pd.notna(row['flow']):
                flow_zscore = abs((row['flow'] - df['flow'].mean()) / df['flow'].std()) if df['flow'].std() > 0 else 0
                if flow_zscore > 2:
                    anomaly_types.append(('flow', row['flow'], flow_zscore))
                    
            if 'turbidity' in row and pd.notna(row['turbidity']):
                turb_zscore = abs((row['turbidity'] - df['turbidity'].mean()) / df['turbidity'].std()) if df['turbidity'].std() > 0 else 0
                if turb_zscore > 2:
                    anomaly_types.append(('turbidity', row['turbidity'], turb_zscore))
            
            for param_type, value, severity_score in anomaly_types:
                severity = 'low' if severity_score < 2.5 else 'medium' if severity_score < 3.5 else 'high' if severity_score < 4.5 else 'critical'
                
                details.append({
                    'id': f"{station}_{row['timestamp'].isoformat()}_{param_type}",
                    'station': station,
                    'timestamp': row['timestamp'],
                    'anomaly_type': param_type,
                    'value': float(value),
                    'severity': severity,
                    'score': float(severity_score),
                    'expected_range': self._get_expected_range(df, param_type)
                })
        
        return details
    
    def _get_expected_range(self, df: pd.DataFrame, param: str) -> str:
        """Calculate expected range for a parameter"""
        if param not in df.columns:
            return "unknown"
        mean = df[param].mean()
        std = df[param].std()
        return f"{mean - 2*std:.2f} to {mean + 2*std:.2f}"

# Threshold-based detection for critical alerts
THRESHOLDS = {
    'temp': {'min': 0, 'max': 30, 'critical_max': 35},
    'flow': {'min': 100, 'max': 5000, 'critical_min': 50},
    'turbidity': {'min': 0, 'max': 100, 'critical_max': 200},
    'dissolved_oxygen': {'min': 4, 'max': 15, 'critical_min': 2},
    'ph': {'min': 6.0, 'max': 9.0}
}

def check_thresholds(reading: Dict) -> List[Dict]:
    """Check if readings exceed safety thresholds"""
    alerts = []
    
    for param, thresholds in THRESHOLDS.items():
        if param not in reading or reading[param] is None:
            continue
            
        value = reading[param]
        
        # Check critical thresholds
        if 'critical_min' in thresholds and value < thresholds['critical_min']:
            alerts.append({
                'type': param,
                'severity': 'critical',
                'message': f"CRITICAL: {param} is {value}, below critical minimum {thresholds['critical_min']}",
                'value': value
            })
        elif 'critical_max' in thresholds and value > thresholds['critical_max']:
            alerts.append({
                'type': param,
                'severity': 'critical',
                'message': f"CRITICAL: {param} is {value}, above critical maximum {thresholds['critical_max']}",
                'value': value
            })
        # Check warning thresholds
        elif value < thresholds['min']:
            alerts.append({
                'type': param,
                'severity': 'warning',
                'message': f"WARNING: {param} is {value}, below normal minimum {thresholds['min']}",
                'value': value
            })
        elif value > thresholds['max']:
            alerts.append({
                'type': param,
                'severity': 'warning',
                'message': f"WARNING: {param} is {value}, above normal maximum {thresholds['max']}",
                'value': value
            })
    
    return alerts
