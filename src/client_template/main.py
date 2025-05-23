import json, os, time, requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

with open("./config.json") as f:
    config = json.load(f)

SERVER_URL = config["server_url"]
CLIENT_ID = config["client_id"]
WATCH_DIR = config["watch_dirs"]

class HoneyfileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            report_access(event.src_path)

def report_access(file_path):
    try:
        data = {
            "client_id": CLIENT_ID,
            "file_path": file_path,
            "event": "modified"
        }
        requests.post(f"{SERVER_URL}/report", json=data)
    except Exception as e:
        print("Failed to send alert:", e)


if __name__ == "__main__":
    event_hander = HoneyfileHandler()
    observer = Observer()
    observer.schedule(event_hander, WATCH_DIR, recursive=True)
    observer.start()

    print(f"[+] Monitoring {WATCH_DIR}")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()