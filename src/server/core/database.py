"""
DOCSTRING:
This module defineds the Database class which manages all interactions with the PostgreSQL database for Capcan.

The Database class provides methods for:
- Establishing and closing database connections
- Managing web users (create, retrieve)
- Client authentication and management (register, revoke, update, delete clients)
- Client status and monitoring (update last seen, get status, update status)
- Telemetry and alerts (store/retrieve telemetry, store/retrieve events, store/retrieve alerts, acknowledge/resolve alerts)
- Configuration management (store/retrieve configurations)
- Testing utilities (clear database, drop tables, clear specific table)

The class uses psycopg2 for database interactions and includes error handling to ensure database integrity.

The class imports environment variables for database connection parameters.
"""

from flask import jsonify
import psycopg2
import os
from dotenv import load_dotenv as load_env
from enum import Enum
import uuid
from ..utils.encryptors import hash_password, pre_hash_client_password


class Database:
    def __init__(self):
        load_env()
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            self.cursor = self.conn.cursor()
            print("Database connection established successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            print("Failed to establish database connection.")

    def close(self):
        if self.conn:
            self.cursor.close()  # closes the cursor
            self.conn.close()  # closes the database connection
            print("Database connection closed.")

    # ============== WEB USER MANAGEMENT ==============
    # Role to permissions mapping
    ROLE_PERMISSIONS = {
        'admin': ['ALL'],
        'analyst': ['READ', 'VIEW', 'WRITE', 'MANAGE'],
        'read-only': ['READ', 'VIEW']
    }

    def create_web_user(self, username, pass_hash, email, role='read-only'):
        user_id = str(uuid.uuid4())
        permissions = self.ROLE_PERMISSIONS.get(role, ['READ', 'VIEW'])
        is_admin = (role == 'admin')
        try:
            self.cursor.execute(
                "INSERT INTO auth (user_id, username, pass_hash) VALUES (%s, %s, %s);",
                (user_id, username, pass_hash),
            )
            self.conn.commit()
            print(f"Web user '{username}' created successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to create web user '{username}'.")

        try:
            self.cursor.execute(
                "INSERT INTO user_permissions (user_id, email, display_name, is_admin, role, permissions) values (%s, %s, %s, %s, %s, %s);",
                (user_id, email, username, is_admin, role, permissions),
            )
            self.conn.commit()
            print(f"User permissions for '{username}' created successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to create user permissions for '{username}'.")

    def create_default_web_user(self):
        load_env()
        default_username = os.getenv("WEB_DEFAULT_USER")
        default_password = os.getenv("WEB_DEFAULT_PASSWORD")
        default_email = os.getenv("WEB_DEFAULT_EMAIL")
        default_exists = self.get_web_user(default_username)
        print(default_exists)
        if default_username and default_password and default_email and not default_exists:
            print(f"Creating default web user '{default_username}'...")
            client_hash = pre_hash_client_password(default_password)
            pass_hash = hash_password(client_hash)
            try:
                # Default user is always admin with all permissions
                self.create_web_user(default_username, pass_hash, default_email, role='admin')
            except (psycopg2.DatabaseError, Exception) as error:
                print(error)
                if self.conn:
                    self.conn.rollback()
                print(f"Failed to create default web user '{default_username}'.")
        else:
            print(f"Default web user '{default_username}' already exists or environment variables are not set.")

    def update_web_user(self, user_id, email=None, display_name=None, role=None, permissions=None):
        pass  # update web user information in the database, used for user management and role/permission updates

    def delete_web_user(self, user_id):
        try:
            self.cursor.execute("DELETE FROM auth WHERE user_id = %s;", (user_id,))
            self.conn.commit()
            print(f"Web user with user_id '{user_id}' deleted successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to delete web user with user_id '{user_id}'.")

    def get_web_user_id(self, username):
        try:
            self.cursor.execute("SELECT user_id FROM user_permissions WHERE display_name = %s", (username,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def get_web_user(self, username):
        try:
            self.cursor.execute("SELECT * FROM user_permissions WHERE display_name = %s", (username,))
            return self.cursor.fetchone()
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None
    
    def get_user_auth(self, username):
        """Retrieve the stored password hash for a given username from the database."""
        try:
            self.cursor.execute(
                "SELECT pass_hash FROM auth WHERE username = %s", (username,)
            )
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    _USER_COLS = ['user_id', 'email', 'display_name', 'is_active', 'is_admin', 'created_at', 'role', 'permissions']

    def get_web_user_by_id(self, user_id):
        """Return the user_permissions row for the given user_id as a dict, or None."""
        try:
            self.cursor.execute(
                "SELECT user_id, email, display_name, is_active, is_admin, created_at, role, permissions "
                "FROM user_permissions WHERE user_id = %s",
                (user_id,)
            )
            row = self.cursor.fetchone()
            return dict(zip(self._USER_COLS, row)) if row else None
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def get_all_web_users(self):
        """Return all user_permissions rows as a list of dicts, ordered newest first."""
        try:
            self.cursor.execute(
                "SELECT user_id, email, display_name, is_active, is_admin, created_at, role, permissions "
                "FROM user_permissions ORDER BY created_at DESC"
            )
            rows = self.cursor.fetchall()
            return [dict(zip(self._USER_COLS, row)) for row in rows]
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return []

    def get_config_by_client(self, client_id):
        pass  # retrieve configuration data for a specific client, used for applying configurations on the client side

    # ============== CLIENT AUTHENTICATION & SECURITY UTILITIES ==============
    def register_client(
        self,
        client_id: str,
        hostname: str,
        client_os: str,
        client_secret: str,
        description: str = None,
        notes: str = None,
        ip_address: str = None,
        ssh_user: str = None,
    ):
        query = """
        INSERT INTO registered_clients (client_id, hostname, client_os, client_secret, description, notes, ip_address, ssh_user)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            self.cursor.execute(
                query,
                (client_id, hostname, client_os, client_secret, description, notes, ip_address, ssh_user),
            )
            self.conn.commit()
            print(
                f"Client '{hostname}' registered successfully with client_id '{client_id}'."
            )
            return True
        except (psycopg2.DatabaseError, Exception) as error:
            if self.conn:
                self.conn.rollback()
            print(f"Failed to register client '{hostname}': {error}")
            raise  # Re-raise the exception for duplicate key or other constraint violations

    def revoke_client(self, client_id: str):
        query = """
        UPDATE registered_clients SET revoked = TRUE
        WHERE client_id = %s
        """
        try:
            self.cursor.execute(query, (client_id,))
            self.conn.commit()
            print(f"Client with client_id '{client_id}' revoked successfully.")
            return True
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to revoke client with client_id '{client_id}'.")
            return False

    def update_client(
        self,
        client_id: str,
        description: str = None,
        secret: str = None,
        notes: str = None,
    ):
        query = "UPDATE registered_clients SET"
        updates = []
        values = []

        if description is not None:
            updates.append("description = %s")
            values.append(description)
        if secret is not None:
            updates.append("client_secret = %s")
            values.append(secret)
        if notes is not None:
            updates.append("notes = %s")
            values.append(notes)

        if not updates:
            return False

        query += " " + ", ".join(updates) + " WHERE client_id = %s"
        values.append(client_id)

        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            print(f"Client '{client_id}' updated successfully.")
            return True
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to update client '{client_id}'.")
            return False

    def delete_client(self, client_id: str):
        query = """
        DELETE FROM registered_clients WHERE client_id = %s
        """
        try:
            self.cursor.execute(query, (client_id,))
            self.conn.commit()
            print(f"Client with client_id '{client_id}' deleted successfully.")
            return True
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            print(f"Failed to delete client with client_id '{client_id}'.")
            return False

    def get_client_id(
        self, client_number: str = None, hostname: str = None, client_os: str = None
    ):
        try:
            if client_number:
                query = (
                    "SELECT client_id FROM registered_clients WHERE client_number = %s"
                )
                self.cursor.execute(query, (client_number,))
            elif hostname:
                query = "SELECT client_id FROM registered_clients WHERE hostname = %s"
                self.cursor.execute(query, (hostname,))
            elif client_os:
                query = "SELECT client_id FROM registered_clients WHERE client_os = %s"
                self.cursor.execute(query, (client_os,))
            else:
                return None

            result = self.cursor.fetchone()
            return result[0] if result else None
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            return None

    def get_many_clients(self, filter_params: dict):
        pass  # retrieve multiple clients based on filter parameters like OS, registration date, etc.

    def get_client_by_id(self, client_id: str = None):
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
        SELECT * FROM registered_clients
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def get_client_secret(self, client_id: str):
        try:
            self.cursor.execute(
                "SELECT client_secret FROM registered_clients WHERE client_id = %s",
                (client_id,),
            )
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def get_client_deploy_info(self, client_id: str) -> dict | None:
        """Return the SSH connection details stored for a client."""
        try:
            self.cursor.execute(
                "SELECT ip_address, ssh_user FROM registered_clients WHERE client_id = %s",
                (client_id,),
            )
            row = self.cursor.fetchone()
            if not row:
                return None
            return {'ip_address': row[0], 'ssh_user': row[1]}
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    # ============== CLIENT STATUS & MONITORING ==============
    def update_client_last_seen(self, client_id: str):
        pass  # update the last seen timestamp for a client in the database

    def get_client_status(self, client_id: str):
        pass  # retrieve the current status of a client from the database

    def update_client_status(self, client_id: str, status: str):
        pass  # update the status of a client (active, inactive, suspended) in the database

    # ============== TELEMETRY & ALERTS ==============
    def store_client_telemetry(self, client_id: str, telemetry_data: dict):
        """Persist a telemetry snapshot to client_telemetry as JSONB. Returns telemetry_id."""
        import json as _json
        import uuid as _uuid
        telemetry_id = str(_uuid.uuid4())
        query = """
        INSERT INTO client_telemetry (client_id, telemetry_id, telemetry)
        VALUES (%s, %s, %s::jsonb)
        """
        try:
            self.cursor.execute(query, (client_id, telemetry_id, _json.dumps(telemetry_data)))
            self.conn.commit()
            return telemetry_id
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to store telemetry for client '{client_id}': {error}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_client_telemetry(
        self, client_id: str, time_range: dict = None, limit: int = 10
    ):
        """Retrieve recent telemetry snapshots for a client, newest first."""
        query = """
        SELECT telemetry, received_at FROM client_telemetry
        WHERE client_id = %s
        ORDER BY received_at DESC
        LIMIT %s
        """
        try:
            self.cursor.execute(query, (client_id, limit))
            rows = self.cursor.fetchall()
            return [{"telemetry": row[0], "timestamp": row[1].isoformat()} for row in rows]
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to get telemetry for client '{client_id}': {error}")
            if self.conn:
                self.conn.rollback()
            return []

    def get_latest_client_telemetry(self, client_id: str):
        """Return the most recent telemetry dict for a client, or None."""
        query = """
        SELECT telemetry, received_at FROM client_telemetry
        WHERE client_id = %s
        ORDER BY received_at DESC
        LIMIT 1
        """
        try:
            self.cursor.execute(query, (client_id,))
            row = self.cursor.fetchone()
            if row:
                return {"telemetry": row[0], "timestamp": row[1]}
            return None
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to get latest telemetry for client '{client_id}': {error}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_active_client_ids(self) -> list:
        """Return a list of client_id strings for all non-revoked clients."""
        try:
            self.cursor.execute(
                "SELECT client_id FROM registered_clients WHERE revoked = false"
            )
            return [row[0] for row in self.cursor.fetchall()]
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to get active client IDs: {error}")
            if self.conn:
                self.conn.rollback()
            return []

    def get_all_clients_with_status(self):
        """
        Return all non-revoked clients with their last telemetry timestamp.
        Each row: (client_id, hostname, client_os, registered_at, last_seen)
        where last_seen is a datetime or None.
        """
        query = """
        SELECT rc.client_id, rc.hostname, rc.client_os, rc.registered_at,
               MAX(ct.received_at) AS last_seen
        FROM registered_clients rc
        LEFT JOIN client_telemetry ct ON rc.client_id = ct.client_id
        WHERE rc.revoked = false
        GROUP BY rc.client_id, rc.hostname, rc.client_os, rc.registered_at
        ORDER BY last_seen DESC NULLS LAST
        """
        cols = ["client_id", "hostname", "client_os", "registered_at", "last_seen"]
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to get clients with status: {error}")
            if self.conn:
                self.conn.rollback()
            return []

    def store_client_event(self, client_id: str, event_type: str, payload: dict):
        pass  # store significant events related to a client (e.g., alerts, errors) in the database

    def get_client_events(
        self,
        client_id: str,
        event_type: str = None,
        time_range: dict = None,
        limit: int = 10,
    ):
        pass  # retrieve events for a client, optionally filtered by event type and time range

    def store_alerts(
        self,
        client_id: str,
        alert_id: str,
        severity: str,
        event_type: str,
        created_at: str,
        score: int = 0,
        status: str = "unresolved",
        rule_id: str = None,
        acknowledged_at: str = None,
        acknowledged_by: str = None,
        details: dict = None,
        tags: list = None,
    ):
        """
        Persist an alert to client_alerts table.
        Try config-style insert first; on failure, rollback and attempt alternate schema insert (title/payload).
        """
        import json

        rule_val = rule_id if rule_id is not None else event_type
        score_val = score if score is not None else 0
        status_val = status if status is not None else "unresolved"

        # Prepare payload/details
        try:
            details_json = json.dumps(details) if isinstance(details, dict) else details
        except Exception:
            details_json = str(details) if details is not None else None

        tags_val = tags if tags else None

        # First attempt: config-style schema (event_type, details, acknowledged_at, acknowledged_by)
        config_query = """
        INSERT INTO client_alerts (client_id, alert_id, rule_id, severity, score, event_type, status, acknowledged_at, acknowledged_by, created_at, details, tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        config_params = (
            client_id,
            alert_id,
            rule_val,
            severity,
            score_val,
            event_type,
            status_val,
            acknowledged_at,
            acknowledged_by,
            created_at,
            details_json,
            tags_val,
        )

        try:
            self.cursor.execute(config_query, config_params)
            self.conn.commit()
            print(
                f"Alert '{alert_id}' stored (config schema) for client '{client_id}'."
            )
            return True
        except (psycopg2.DatabaseError, Exception) as e:
            # rollback and try alternate schema
            if self.conn:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            print(f"Config-style insert failed, will try alternate schema: {e}")

    def get_alerts_by_client(self, client_id, status=None, limit=50):
        """Retrieve alerts for a specific client, optionally filtered by status and limited in number."""
        search_query = """
        SELECT * FROM client_alerts WHERE client_id = %s AND status = %s ORDER BY created_at DESC LIMIT %s
        """
        params = (client_id, status, limit) if status else (client_id, limit)
        try:
            self.cursor.execute(search_query, params)
            return self.cursor.fetchall()
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            if self.conn:
                self.conn.rollback()
            return None

    def acknowledge_alert(self, alert_id):
        pass  # mark an alert as acknowledged in the database, indicating it has been seen by an analyst

    def resolve_alert(self, alert_id):
        pass  # mark an alert as resolved in the database, indicating it has been addressed and is no longer active

    # ============== CHANGES =========================
    def store_change(
        self,
        client_id,
        change_id,
        change_type,
        name,
        initiated_by,
        previous_state=None,
        new_state=None,
        description=None,
        tags=None,
    ):
        pass  # store a change record in the database for tracking configuration changes, client modifications, etc.

    def get_changes_by_client(self, client_id, status=None, time_range=None, limit=10):
        pass  # retrieve change records for a specific client, optionally filtered by status and time range

    def update_change_status(self, change_id, status):
        pass  # update the status of a change record (e.g., pending, approved, rejected) in the database

    # ============== CONFIGURATIONs ==================
    def set_pending_config(self, client_ids: list, settings: dict) -> int:
        """
        Push a pending settings update to one or more clients.
        Inserts a new row into client_configs for each client_id with applied_at=NULL.
        Returns the number of rows inserted.
        """
        import json as _json
        import uuid as _uuid
        count = 0
        for cid in client_ids:
            config_id = str(_uuid.uuid4())
            try:
                self.cursor.execute(
                    """
                    INSERT INTO client_configs (client_id, config_id, config, updated_at, applied_at)
                    VALUES (%s, %s, %s::jsonb, NOW(), NULL)
                    """,
                    (cid, config_id, _json.dumps(settings)),
                )
                count += 1
            except (psycopg2.DatabaseError, Exception) as error:
                print(f"Failed to set pending config for client '{cid}': {error}")
                if self.conn:
                    self.conn.rollback()
                return count
        self.conn.commit()
        return count

    def deliver_pending_config(self, client_id: str):
        """
        Atomically retrieve the latest pending (unapplied) config for a client
        and mark it as applied. Returns the settings dict, or None if no pending config.
        """
        try:
            self.cursor.execute(
                """
                SELECT config_id, config FROM client_configs
                WHERE client_id = %s AND applied_at IS NULL
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (client_id,),
            )
            row = self.cursor.fetchone()
            if not row:
                return None
            config_id, settings = row
            self.cursor.execute(
                "UPDATE client_configs SET applied_at = NOW() WHERE config_id = %s",
                (config_id,),
            )
            self.conn.commit()
            return settings  # already a dict (psycopg2 auto-decodes JSONB)
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to deliver pending config for client '{client_id}': {error}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_effective_settings(self, client_id: str):
        """Return the most recently applied settings dict for a client, or None."""
        try:
            self.cursor.execute(
                """
                SELECT config FROM client_configs
                WHERE client_id = %s AND applied_at IS NOT NULL
                ORDER BY applied_at DESC
                LIMIT 1
                """,
                (client_id,),
            )
            row = self.cursor.fetchone()
            return row[0] if row else None
        except (psycopg2.DatabaseError, Exception) as error:
            print(f"Failed to get effective settings for client '{client_id}': {error}")
            if self.conn:
                self.conn.rollback()
            return None

    def store_configuration(self, client_id, config_id, config_name, config_data):
        pass  # store configuration data in the database

    def get_configuration(self, client_id, config_name=None):
        pass  # retrieve configuration data for a specific client and configuration name

    # ============== TESTING & ADMIN =================
    def clear_database(self):  # util, clear all tables in the database, used in testing
        if self.conn:
            try:
                with self.cursor as cursor:
                    select_tables_query = """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                    """

                    cursor.execute(select_tables_query)
                    tables = cursor.fetchall()
                    for table in tables:
                        clean_table = f"TRUNCATE TABLE {table[0]} CASCADE;"
                        cursor.execute(clean_table)

            except psycopg2.errors as error:
                print(error)
                if self.conn:
                    self.conn.rollback()
                print("Failed to retrieve or clean tables.")
        else:
            print("Database connection failed. Cannot clean tabels")

    def drop_tables(self):  # util, drop all tables in the database, used in testing
        if self.conn:
            try:
                with self.cursor as cursor:
                    select_tables_query = """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                    """

                    cursor.execute(select_tables_query)
                    tables = cursor.fetchall()
                    for table in tables:
                        drop_query = f"DROP TABLE IF EXISTS {table[0]} CASCADE;"
                        try:
                            cursor.execute(drop_query)
                        except psycopg2.Error as error:
                            print(
                                f"Error occured while dropping table '{table[0]}': {error}"
                            )

            except psycopg2.Error as error:
                if self.conn:
                    self.conn.rollback()
                print("Failed to retrieve or drop tables.")

        else:
            print("Database connection failed. Cannot clean tabels")

    def clear_table(self, table):  # util, clear specified table, used in testing.
        try:
            clean_table = f"TRUNCATE TABLE {table} CASCADE;"
            self.cursor.execute(clean_table)
            self.conn.commit()
        except psycopg2.Error as error:
            if self.conn:
                self.conn.rollback()
            print(f"Cleanup failed: {error}")


if __name__ == "__main__":
    db = Database()
    if db.conn:
        print("Database connection test successful.")
    else:
        print("Database connection test failed.")
