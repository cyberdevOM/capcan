import json, os, time, requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

with open("config.json") as f:
    config = json.load(f)

SERVER_URL = config["server_url"]
CLIENT_ID = config["client_id"]
WATCH_DIR = config["watch_dir"]

