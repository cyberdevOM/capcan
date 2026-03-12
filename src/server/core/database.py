import psycopg2
import os
from dotenv import load_dotenv as load_env
from enum import Enum

class Database:
    def __init__(self):
        load_env()
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD")
            ) # creates a connection to the database using credentials from environment variables
            self.cursor = self.conn.cursor() # creates a cursor object for executing SQL commands
            print("Database connection established successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            print("Failed to establish database connection.")

    def close(self):
        if self.conn:
            self.cursor.close() # closes the cursor
            self.conn.close() # closes the database connection
            print("Database connection closed.")


# ============== WEB USER MANAGEMENT ==============
    def create_web_user(self, username, pass_hash):
        try:    
            self.cursor.execute(
                "INSERT INTO auth (username, pass_hash) VALUES (%s, %s);",
                (username, pass_hash)
            )
            self.conn.commit()
            print(f"Web user '{username}' created successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to create web user '{username}'.")

    def get_web_user(self, username):
        pass # retrieve web user information from the database for authentication and user management

    def get_config_by_client(self, client_id):
        pass # retrieve configuration data for a specific client, used for applying configurations on the client side

# ============== CLIENT AUTHENTICATION & SECURITY UTILITIES ==============
    def register_client(self, Client_id, hostname, description, client_secret):
        query = """
        INSERT INTO registered_clients (client_id, hostname, description, client_secret)
        VALUES (%s, %s, %s, %s);
        """
        try:
            self.cursor.execute(query, (Client_id, hostname, description, client_secret))
            self.conn.commit()
            print(f"Client '{hostname}' registered successfully with client_id '{Client_id}'.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to register client '{hostname}'.")

    def revoke_client(self, client_id):
        query = """
        UPDATE registered_clients WHERE client_id = %s
        SET revoked = TRUE;
        """
        try:
            self.cursor.execute(query, (client_id,))
            self.conn.commit()
            print(f"Client with client_id '{client_id}' revoked successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to revoke client with client_id '{client_id}'.")

    def update_client(self, client_id, description=None, secret=None, notes=None):
        query = """
        UPDATE registered_clients WHERE client_id = %s
        """
        
        # Dynamically build the SET clause based on which parameters are provided
        pass
        
    def delete_client(self, client_id):
        query = """
        DELETE FROM registered_clients WHERE CLIENT_ID = %s CASCADE;
        """
        try:
            self.cursor.execute(query, (client_id,))
            self.conn.commit()
            print(f"Client with client_id '{client_id}' deleted successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to delete client with client_id '{client_id}'.")

    def get_client_id(self, client_number=None, hostname=None, client_os=None):
        query = """
        SELECT client_id FROM registered_clients
        WHERE
        """
        # Dynamically build the WHERE clause based on which parameters are provided
        pass

    
    def get_many_clients(self, filter_params):
        pass # retrieve multiple clients based on filter parameters like OS, registration date, etc.
    
    def get_client_by_id(self, client_id):
        query = """
        SELECT * FROM registered_clients WHERE client_id = %s;
        """
        try:
            self.cursor.execute(query, (client_id,))
            return self.cursor.fetchone()
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def get_all_clients(self):
        query = """
        SELECT * FROM registered_clientsl
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall() # returns a list of all clients in the database
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None
        

    def get_client_secret(self, client_id):
        try:
            self.cursor.execute(
                "SELECT client_secret FROM registered_clients WHERE client_id = %s:",
                (client_id,)
            )
            result = self.cursor.fetchone()
            if result:
                return result[0] # returns the client_secret if found
            else:
                return None # returns None if client_id is not found
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None
        
# ============== CLIENT STATUS & MONITORING ==============
    def update_client_last_seen(self, client_id):
        pass # update the last seen timestamp for a client in the database

    def get_client_status(self, client_id):
        pass # retrieve the current status of a client from the database

    def update_client_status(self, client_id, status):
            pass # update the status of a client (active, inactive, suspended) in the database

# ============== TELEMETRY & ALERTS ==============
    def store_client_telemetry(self, client_id, telemetry_data):
        pass # store incoming telemetry data from clients in the database

    def get_client_telemetry(self, client_id, time_range=None, limit=10):
        pass # retrieve telemetry data for a client, optionally filtered by a time range

    def store_client_event(self, client_id, event_type, payload):
        pass # store significant events related to a client (e.g., alerts, errors) in the database

    def get_client_events(self, client_id, event_type=None, time_range=None, limit=10):
        pass # retrieve events for a client, optionally filtered by event type and time range

    def store_alerts(self, client_id, alert_id, severity, event_type, title, description):
        pass # store generated alerts in the database for later retrieval and display on the dashboard

    def get_alerts_by_client(self, client_id, status=None, limit=50):
        pass # retrieve alerts for a specific client, optionally filtered by status (active, resolved)

    def acknowledge_alert(self, alert_id):
        pass # mark an alert as acknowledged in the database, indicating it has been seen by an analyst

    def resolve_alert(self, alert_id):
        pass # mark an alert as resolved in the database, indicating it has been addressed and is no longer active

# ============== CHANGES =========================
    def store_change(self, client_id, change_id, change_type, name, initiated_by, 
                     previous_state=None, new_state=None, description=None, tags=None):
        pass # store a change record in the database for tracking configuration changes, client modifications, etc.

    def get_changes_by_client(self, client_id, status=None, time_range=None, limit=10):
        pass # retrieve change records for a specific client, optionally filtered by status and time range

    def update_change_status(self, change_id, status):
        pass # update the status of a change record (e.g., pending, approved, rejected) in the database

# ============== CONFIGURATIONs ==================
    def store_configuration(self, client_id, config_id, config_name, config_data):
        pass # store configuration data in the database

    def get_configuration(self, client_id, config_name=None):
        pass # retrieve configuration data for a specific client and configuration name

if __name__ == "__main__":
    db = Database()
    if db.conn:
        print("Database connection test successful.")
    else:
        print("Database connection test failed.")