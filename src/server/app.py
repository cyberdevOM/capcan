import json, time, os
from builder import Build_client 
from services import ClientServices
from configurator import Server_configurator, Client_configurator


def load_config(config_path):
    if not os.path.exists(config_path):
        print("[!] Configuration file not found. Please run the configurator first.")
        return None
    with open(config_path) as f:
        return json.load(f)

def main():
    Client = Client_configurator()
    # Server = Server_configurator()
    Build = Build_client()

    config_path = os.path.join(os.path.dirname(__file__), "..", "client_template", "config.json")
    Client_config = load_config(config_path)
    
    while True:
        print("\n1. Build Client Config")
        print("2. build Client")
        print("3. Exit")
        choice = input("Choose an option: ").strip()

        match choice:
            case "1":
                Client.run_client_configurator()
            case "2":
                if not os.path.getsize(config_path) > 0:
                    print("Please build a client config first.")
                    break
                
                Build.build(Client_config)
            case "3":
                print("Exiting...")
                break
            case _:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
    
    