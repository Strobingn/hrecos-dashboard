from typing import Dict, List

# Try to import heavy ML deps — gracefully degrade if unavailable (mobile mode)
try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class AnomalyDetector:
    """AI-powered anomaly detection. Falls back to threshold-only on mobile."""

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.is_fitted = False
        if ML_AVAILABLE:
            self.scaler = StandardScaler()
            self.model = None

    def prepare_features(self, df):
        feature_cols = [c for c in ["temp", "flow", "turbidity", "dissolved_oxygen", "ph"]
                        if c in df.columns]
        features = df[feature_cols].copy().fillna(df[feature_cols].mean())
        if len(features) > 1:
            features["temp_change"] = features["temp"].diff().fillna(0)
            features["flow_change"] = features.get("flow", features["temp"] * 0).diff().fillna(0)
        else:
            features["temp_change"] = 0
            features["flow_change"] = 0
        return features.values

    def fit(self, df) -> "AnomalyDetector":
        if not ML_AVAILABLE or len(df) < 10:
            return self
        features = self.prepare_features(df)
        scaled = self.scaler.fit_transform(features)
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        self.model.fit(scaled)
        self.is_fitted = True
        return self

    def detect(self, df):
        if not ML_AVAILABLE or not self.is_fitted or len(df) < 1:
            df["anomaly"] = 1
            df["anomaly_score"] = 0.5
            return df
        features = self.prepare_features(df)
        scaled = self.scaler.transform(features)
        df = df.copy()
        df["anomaly"] = self.model.predict(scaled)
        df["anomaly_score"] = self.model.decision_function(scaled)
        return df

    def get_anomaly_details(self, df, station: str) -> List[Dict]:
        if not ML_AVAILABLE:
            return []
        anomalies = df[df["anomaly"] == -1].copy()
        details = []
        for _, row in anomalies.iterrows():
            for param in ["temp", "flow", "turbidity"]:
                if param not in row or pd.isna(row[param]):
                    continue
                std = df[param].std()
                zscore = abs((row[param] - df[param].mean()) / std) if std > 0 else 0
                if zscore > 2:
                    severity = ("low" if zscore < 2.5 else
                                "medium" if zscore < 3.5 else
                                "high" if zscore < 4.5 else "critical")
                    details.append({
                        "id": f"{station}_{row['timestamp'].isoformat()}_{param}",
                        "station": station,
                        "timestamp": row["timestamp"],
                        "anomaly_type": param,
                        "value": float(row[param]),
                        "severity": severity,
                        "score": float(zscore),
                        "expected_range": self._get_expected_range(df, param),
                    })
        return details

    def _get_expected_range(self, df, param: str) -> str:
        if param not in df.columns:
            return "unknown"
        mean, std = df[param].mean(), df[param].std()
        return f"{mean - 2*std:.2f} to {mean + 2*std:.2f}"


# Threshold-based detection (no ML deps required)
THRESHOLDS = {
    "temp":             {"min": 32, "max": 86, "critical_max": 95},   # °F
    "flow":             {"min": 100, "max": 5000, "critical_min": 50},
    "turbidity":        {"min": 0, "max": 100, "critical_max": 200},
    "dissolved_oxygen": {"min": 4, "max": 15, "critical_min": 2},
    "ph":               {"min": 6.0, "max": 9.0},
}


def check_thresholds(reading: Dict) -> List[Dict]:
    alerts = []
    for param, thresholds in THRESHOLDS.items():
        value = reading.get(param)
        if value is None:
            continue
        if "critical_min" in thresholds and value < thresholds["critical_min"]:
            alerts.append({"type": param, "severity": "critical",
                           "message": f"CRITICAL: {param} {value} below critical min {thresholds['critical_min']}",
                           "value": value})
        elif "critical_max" in thresholds and value > thresholds["critical_max"]:
            alerts.append({"type": param, "severity": "critical",
                           "message": f"CRITICAL: {param} {value} above critical max {thresholds['critical_max']}",
                           "value": value})
        elif value < thresholds["min"]:
            alerts.append({"type": param, "severity": "warning",
                           "message": f"WARNING: {param} {value} below normal min {thresholds['min']}",
                           "value": value})
        elif value > thresholds["max"]:
            alerts.append({"type": param, "severity": "warning",
                           "message": f"WARNING: {param} {value} above normal max {thresholds['max']}",
                           "value": value})
    return alerts
