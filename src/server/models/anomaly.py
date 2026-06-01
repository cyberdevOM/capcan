import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class TelemetryAnomalyDetector:
    """
    Isolation Forest-based anomaly detector for telemetry data.

    Replaces the previous One-Class SVM implementation. Scales features
    internally so raw telemetry dicts can be passed directly via
    anomaly_score().

    Features expected (in order):
        cpu_percent, memory_percent, disk_usage, network_io, process_count
    """

    FEATURES = ["cpu_percent", "memory_percent", "disk_usage", "network_io", "process_count"]

    def __init__(self, n_estimators=200, contamination=0.01, random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X):
        """
        Fit on telemetry data.
        X: array-like of shape (n_samples, 5)
        """
        X = np.asarray(X, dtype=np.float32)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True

    def predict(self, X):
        """
        Returns 1 (normal) or -1 (anomaly) for each sample.
        X: array-like of shape (n_samples, 5)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction.")
        X = np.asarray(X, dtype=np.float32)
        return self.model.predict(self.scaler.transform(X))

    def anomaly_score(self, X):
        """
        Returns a normalised anomaly score in [0, 1] for each sample.
        Higher = more anomalous.
        X: array-like of shape (n_samples, 5)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before scoring.")
        X = np.asarray(X, dtype=np.float32)
        raw = -self.model.decision_function(self.scaler.transform(X))
        return np.clip(raw, 0, 1)
