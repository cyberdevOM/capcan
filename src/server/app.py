import json
import requests
import time
from builder import Build_client
from services import ClientService

def load_config():
    with open("../src/client_template/config.json") as f:
        return json.load(f)

def build_config():
    print("[*] Build configuration...")
    config = {
        "client_id": input("Enter")
    }