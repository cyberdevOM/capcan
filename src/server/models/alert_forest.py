import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Severity bands define the score range each severity level occupies on the
# 1-100 scale. The Isolation Forest anomaly score then modulates the position
# within that band — so a highly anomalous critical alert scores closer to 100
# while a routine critical alert sits near 80.
SEVERITY_BANDS = {
    "info":     (1,  20),
    "low":      (20, 40),
    "medium":   (40, 60),
    "high":     (60, 80),
    "critical": (80, 100),
}
SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]


class AlertScorer:
    """
    Scores alerts on a 1-100 criticality scale using Isolation Forest.

    Scoring logic:
    - Severity determines the score band (e.g. critical → 80-100).
    - The IF anomaly score for the accompanying telemetry modulates the
      position within that band.
    - No model required at runtime: falls back to the band midpoint if
      not fitted, so the server can start before training is complete.

    Features expected for fit() and score_alert():
        [cpu_percent, memory_percent, disk_usage, network_io,
         process_count, severity_encoded]
    """

    FEATURES = [
        "cpu_percent", "memory_percent", "disk_usage",
        "network_io", "process_count", "severity_encoded",
    ]

    def __init__(self, n_estimators=200, contamination=0.01, random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(self, X):
        """
        Fit on historical alert feature vectors.
        X: array-like of shape (n_samples, 6) — 5 telemetry + severity_encoded.
        """
        X = np.asarray(X, dtype=np.float32)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def encode_severity(severity: str) -> float:
        """Maps a severity string to a numeric index [0, 4]."""
        key = (severity or "medium").lower()
        return float(SEVERITY_ORDER.index(key) if key in SEVERITY_ORDER else 2)

    # ── Scoring ───────────────────────────────────────────────────────────────

    def score_alert(self, telemetry: dict, severity: str) -> int:
        """
        Score a single alert on a 1-100 criticality scale.

        Args:
            telemetry: dict with keys cpu_percent, memory_percent, disk_usage,
                       network_io, process_count (missing keys default to 0).
            severity:  'info' | 'low' | 'medium' | 'high' | 'critical'

        Returns:
            Integer score in [1, 100].
        """
        sev = (severity or "medium").lower()
        band_low, band_high = SEVERITY_BANDS.get(sev, (40, 60))

        if self.is_fitted:
            features = np.array([[
                telemetry.get("cpu_percent", 0),
                telemetry.get("memory_percent", 0),
                telemetry.get("disk_usage", 0),
                telemetry.get("network_io", 0),
                telemetry.get("process_count", 0),
                self.encode_severity(sev),
            ]], dtype=np.float32)
            X_scaled = self.scaler.transform(features)
            # decision_function returns positive for inliers; negate so
            # higher values mean more anomalous.
            raw = float(-self.model.decision_function(X_scaled)[0])
            # Clamp and normalise to [0, 1] — typical raw range is ~[-0.5, 0.5]
            norm = float(np.clip((raw + 0.5), 0.0, 1.0))
        else:
            norm = 0.5  # band midpoint when model is not yet available

        score = band_low + norm * (band_high - band_low)
        return int(np.clip(round(score), 1, 100))

    def score_batch(self, records: list[dict]) -> list[int]:
        """
        Score a list of alert records.
        Each record must have a 'severity' key and optionally telemetry keys.
        Returns a list of integer scores in [1, 100].
        """
        return [
            self.score_alert(rec, rec.get("severity", "medium"))
            for rec in records
        ]
