"""
fit_models.py

Reads pregenerated training data from all_clients.jsonl.gz and fits both
the TelemetryAnomalyDetector (Isolation Forest) and AlertScorer
(Isolation Forest + severity bands), then saves them to models/pretrained/.

Memory-efficient: streams data using reservoir sampling rather than loading
all 50M records at once.

Usage:
    python -m src.server.models.training.fit_models
    python -m src.server.models.training.fit_models --data ./path/to/all_clients.jsonl.gz
"""

import argparse
import gzip
import json
import os
import sys
import random
import numpy as np
import joblib

here = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(here, "..", "pretrained")
DEFAULT_DATA = os.path.join(here, "simulated_telemetry", "all_clients.jsonl.gz")

ANOMALY_DETECTOR_PATH = os.path.join(models_dir, "telemetry_anomaly_detector.joblib")
ALERT_SCORER_PATH     = os.path.join(models_dir, "alert_scorer.joblib")

TELEMETRY_FEATURES = ["cpu_percent", "memory_percent", "disk_usage", "network_io", "process_count"]

# Severity distribution used to synthesise the severity column during training.
# anomaly=False → mostly info/low;  anomaly=True → mostly high/critical
SEVERITY_NORMAL_WEIGHTS   = [0.35, 0.35, 0.20, 0.08, 0.02]  # info low med high crit
SEVERITY_ANOMALY_WEIGHTS  = [0.02, 0.08, 0.20, 0.40, 0.30]
SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]

ANOMALY_DETECTOR_SAMPLES = 500_000
ALERT_SCORER_SAMPLES     = 500_000


def reservoir_sample(path, n):
    """Pick n random records from the file without loading all data into memory."""
    reservoir = []
    count = 0
    opener = gzip.open if path.endswith(".gz") else open

    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                row = {feat: entry[feat] for feat in TELEMETRY_FEATURES}
                row["anomaly"] = bool(entry.get("anomaly", False))
            except (json.JSONDecodeError, KeyError):
                continue

            count += 1
            if len(reservoir) < n:
                reservoir.append(row)
            else:
                j = random.randint(0, count - 1)
                if j < n:
                    reservoir[j] = row

            if count % 1_000_000 == 0:
                print(f"  Scanned {count:,} records, sampled {len(reservoir):,}")

    print(f"  Done. Scanned {count:,} total, sampled {len(reservoir):,}.")
    return reservoir


def build_telemetry_array(records):
    """Extract the 5 telemetry feature columns as a float32 array."""
    return np.array(
        [[r[f] for f in TELEMETRY_FEATURES] for r in records],
        dtype=np.float32,
    )


def build_scorer_array(records):
    """
    Build the 6-column feature array for AlertScorer:
    5 telemetry features + severity_encoded.
    Severity is synthesised from the anomaly flag using realistic distributions.
    """
    rows = []
    for r in records:
        weights = SEVERITY_ANOMALY_WEIGHTS if r["anomaly"] else SEVERITY_NORMAL_WEIGHTS
        sev_idx = float(random.choices(range(5), weights=weights)[0])
        rows.append([r[f] for f in TELEMETRY_FEATURES] + [sev_idx])
    return np.array(rows, dtype=np.float32)


def fit_anomaly_detector(X):
    from src.server.models.anomaly import TelemetryAnomalyDetector
    print(f"\nFitting TelemetryAnomalyDetector (IF) on {len(X):,} samples...")
    model = TelemetryAnomalyDetector(n_estimators=200, contamination=0.01, random_state=42)
    model.fit(X)
    print("  Done.")
    return model


def fit_alert_scorer(X):
    from src.server.models.alert_forest import AlertScorer
    print(f"\nFitting AlertScorer (IF) on {len(X):,} samples...")
    model = AlertScorer(n_estimators=200, contamination=0.01, random_state=42)
    model.fit(X)
    print("  Done.")
    return model


def save_model(model, path, label):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  {label} saved -> {path} ({size_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Fit and save anomaly detection models.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="Path to training data (.jsonl or .jsonl.gz)")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: Training data not found at: {args.data}", file=sys.stderr)
        sys.exit(1)

    print(f"=== Sampling {ANOMALY_DETECTOR_SAMPLES:,} records ===")
    records = reservoir_sample(args.data, ANOMALY_DETECTOR_SAMPLES)

    X_telemetry = build_telemetry_array(records)
    X_scorer    = build_scorer_array(records)

    anomaly_model = fit_anomaly_detector(X_telemetry)
    scorer_model  = fit_alert_scorer(X_scorer)

    print("\nSaving models...")
    save_model(anomaly_model, ANOMALY_DETECTOR_PATH, "TelemetryAnomalyDetector")
    save_model(scorer_model,  ALERT_SCORER_PATH,     "AlertScorer")

    print("\nAll models fitted and saved. Ready for production.")


if __name__ == "__main__":
    main()
