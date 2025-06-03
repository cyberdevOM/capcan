# Configurator for server settings, IP, PORT, etc.

import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "server_config.json")

def prompt_ip(prompt_text):
    while True:
        ip = input(f"{prompt_text}: ").strip()
        parts = ip.split('.')
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) < 255 for part in parts):
            return ip
        print("Invalid IP address. Please enter a valid IPv4 address in the format x.x.x.x where x is between 0 and 255.")

def prompt_port(prompt_text):
    while True:
        port = input(f"{prompt_text}: ").strip()
        if port.isdigit() and 0 < int(port) < 65535: # add checks for other ports that could be taken by other services
            return int(port)
        print("Invalid port number. Please enter a valid port number between 1 and 65535.")

def prompt_yes_no(prompt_text):
    while True:
        val = input(f"{prompt_text} (y/n): ").strip().lower()
        if val in ('y', 'n'):
            return val == 'y'
        print("Please enter 'y' or 'n'.")

def run_configurator():
    print("=== Server Configuration ===")
    config = {}
    config['server_ip'] = prompt_ip("Enter server IP address")
    config['server_port'] = prompt_port("Enter server port")
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Configuration saved to {CONFIG_PATH}")

if __name__ == "__main__":
    run_configurator()