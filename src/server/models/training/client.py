import os
import random
import json
import gzip
from datetime import datetime, timedelta

NUM_CLIENTS = 5000
REPORT_INTERVAL = 60  # seconds
DAYS = 7
DATA_DIR = "./simulated_telemetry"

FEATURES = ["cpu_percent", "memory_percent", "disk_usage", "network_io", "process_count"]

# Simulate normal and anomalous telemetry
NORMAL_RANGES = {
    "cpu_percent": (5, 40),
    "memory_percent": (10, 60),
    "disk_usage": (20, 80),
    "network_io": (100, 1000),
    "process_count": (50, 200)
}
ANOMALY_PROB = 0.01  # 1% chance per report
ANOMALY_BOOST = {
    "cpu_percent": (80, 100),
    "memory_percent": (80, 100),
    "disk_usage": (90, 100),
    "network_io": (2000, 5000),
    "process_count": (300, 500)
}

def simulate_telemetry(client_id, ts):
    telemetry = {}
    is_anomaly = random.random() < ANOMALY_PROB
    for feat in FEATURES:
        if is_anomaly and random.random() < 0.5:
            lo, hi = ANOMALY_BOOST[feat]
        else:
            lo, hi = NORMAL_RANGES[feat]
        telemetry[feat] = round(random.uniform(lo, hi), 2)
    telemetry["timestamp"] = ts.isoformat()
    telemetry["client_id"] = client_id
    telemetry["anomaly"] = is_anomaly
    return telemetry

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    output_file = os.path.join(DATA_DIR, "all_clients.jsonl.gz")
    start = datetime.utcnow()
    end = start + timedelta(days=DAYS)
    timestamps = [
        start + timedelta(seconds=i * REPORT_INTERVAL)
        for i in range(int((end - start).total_seconds() // REPORT_INTERVAL))
    ]
    total_rounds = len(timestamps)
    total_entries = total_rounds * NUM_CLIENTS

    print(f"Pregenerating {NUM_CLIENTS} clients × {total_rounds} rounds = {total_entries:,} entries")
    print(f"Output: {output_file}")

    with gzip.open(output_file, "wt", encoding="utf-8") as f:
        for i, ts in enumerate(timestamps):
            for client in range(NUM_CLIENTS):
                client_id = f"client_{client:04d}"
                entry = simulate_telemetry(client_id, ts)
                f.write(json.dumps(entry) + "\n")
            if i % 60 == 0:
                pct = (i / total_rounds) * 100
                print(f"  Round {i+1}/{total_rounds} ({pct:.1f}%)")

    print(f"Done. Data stored in: {output_file}")

if __name__ == "__main__":
    main()
