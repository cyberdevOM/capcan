# Configurator for server settings, IP, PORT, etc.

import os, json, re, random
from datetime import datetime
class Server_configurator: # configurator for server side settings, IP, PORT, WebAdress, e.g.
    def __init__(self):
        self.CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

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
    
    # web address (ip port and vanity url) for web interface

    def run_server_configurator(self):

        print("=== Server Configuration ===")
        config = {}
        config['server_ip'] = self.prompt_ip("Enter server IP address")
        config['server_port'] = self.prompt_port("Enter server port")
        # add config options as needed
        
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

        print(f"Configuration saved to {self.CONFIG_PATH}")

class Client_configurator:
    def __init__(self):
        self.CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "client_template", "config.json")
        self.home_dir = os.path.expanduser("~")
        self.watching_dirs = {
            "linux": ["/etc/", "/var/log/", os.path.join(self.home_dir, "Documents")],
            "windows": ["C:\\Program Files\\", "C:\\Program Files (x86)\\", ],
        }

    def prompt_server_url(self):
        while True:
            url = input("Enter server URL (e.g., http://example.com): ").strip()
            if url.startswith("http://") or url.startswith("https://") and re.fullmatch(r":\d{4,6}", url):
                return url
            else:
                print("Invalid URL. Please enter a valid URL (http(s)://example.com:9090)")

    def prompt_platform(self):
        while True:
            platforms = ["deb", "debian", "rpm", "RedHat", "Fedora", "windows", "win"]
            platform = input("Enter platform (e.g., deb, rpm, Windows): ").strip()
            if platform and platform.lower() in platforms:
                # Normalize platform name
                if platform.lower() == "win": 
                    platform = "windows" 
                if platform.lower() in ["deb", "debian"]:
                    platform = "deb"
                elif platform.lower() in ["rpm", "redhat", "fedora"]:
                    platform = "rpm"

                return platform
            print("Platform cannot be empty. Please enter a valid platform name.")

    def build_client_id(self, platform):
        # Generate a client ID based on the platform and linier client naming convention
        rand6 = f"{random.randint(0, 999999):06d}" # 6-digit random number
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        return f"{platform}_{rand6}_{timestamp}"
    
    def run_client_configurator(self): # per client configurator
        print("=== Client Configuration ===")
        config = {}
        config['server_url'] = self.prompt_server_url()
        config['platform'] = platform = self.prompt_platform() # defined platform as var to pass into watching_dirs
        config['client_id'] = self.build_client_id(platform)
        config['watch_dirs'] = self.watching_dirs.get(platform.lower(), []) # get watching dirs based on platform
        
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

        print(f"Configuration saved to {self.CONFIG_PATH}")
        #! temp for testing until web interface is ready

