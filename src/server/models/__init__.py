import os
import joblib

from .anomaly import TelemetryAnomalyDetector
from .alert_forest import AlertScorer

pretrained_dir = os.path.join(os.path.dirname(__file__), "pretrained")
anomaly_detector_path = os.path.join(pretrained_dir, "telemetry_anomaly_detector.joblib")
alert_scorer_path     = os.path.join(pretrained_dir, "alert_scorer.joblib")


def load_pretrained_models():
    """
    Load pretrained models from disk.
    Returns (TelemetryAnomalyDetector, AlertScorer) or (None, None)
    if models have not been fitted yet.
    Both models are safe to use unfitted — they fall back gracefully.
    """
    anomaly_model = None
    scorer_model  = None

    if os.path.exists(anomaly_detector_path):
        anomaly_model = joblib.load(anomaly_detector_path)
        print("[models] TelemetryAnomalyDetector loaded.")
    else:
        print("[models] WARNING: No pretrained TelemetryAnomalyDetector found.")

    if os.path.exists(alert_scorer_path):
        scorer_model = joblib.load(alert_scorer_path)
        print("[models] AlertScorer loaded.")
    else:
        print("[models] WARNING: No pretrained AlertScorer found.")

    return anomaly_model, scorer_model
