from .database import Database as database
import psycopg2

class Config:
    def __init__(self):
        self.db = database()
        self.conn = self.db.conn
        self.curs = self.db.cursor

    def create_tables(self):
        try:
            self.registered_clients(self.curs)
            self.client_telemetry(self.curs)
            self.client_event(self.curs)
            self.client_alert(self.curs)
            self.client_changes(self.curs)
            self.client_configs(self.curs)
            self.server_details(self.curs)
            self.auth(self.curs)
            self.user_permissions(self.curs)
            self.client_organizations(self.curs)
            self.notification_integrations(self.curs)
            self.server_audit_logs(self.curs)
            self.conn.commit()
            print("Tables created successfully.")
        except Exception as error:
            print(error)
            self.conn.rollback()

    def create_enums(self):
        enums = {
            "STATUS": "CREATE TYPE STATUS AS ENUM ('active', 'inactive', 'suspended');",
            "ALERT_SEVERITY": "CREATE TYPE ALERT_SEVERITY AS ENUM ('critical', 'high','medium','low', 'info', 'undefined');",
            "ALERT_STATUS": "CREATE TYPE ALERT_STATUS AS ENUM ('unresolved', 'acknowledged', 'resolved');",
            "CHANGE_STATUS": "CREATE TYPE CHANGE_STATUS AS ENUM ('active', 'inactive', 'pending', 'approved', 'rejected');"
        }
        try:
            for enum_name, query in enums.items():
                try:
                    self.curs.execute(query)
                    self.conn.commit()
                except psycopg2.Error as e:
                    self.conn.rollback()
                    if "already exists" in str(e):
                        print(f"Enum {enum_name} already exists, skipping.")
                    else:
                        raise
            print("Enums created successfully.")
        except Exception as error:
            print(error)

    def registered_clients(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS registered_clients (
            client_id VARCHAR(255) PRIMARY KEY NOT NULL,
            client_number SERIAL UNIQUE NOT NULL,
            hostname VARCHAR(255) NOT NULL,
            client_os VARCHAR(255) DEFAULT NULL,
            description TEXT DEFAULT NULL,
            client_secret VARCHAR(255) NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE,
            notes TEXT DEFAULT NULL
        );
        """

        cursor.execute(query)

    def client_telemetry(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_telemetry (
            client_id VARCHAR(255) NOT NULL,
            telemetry_id VARCHAR(255) PRIMARY KEY NOT NULL,
            status STATUS DEFAULT 'active',
            telemetry JSONB DEFAULT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_call TIMESTAMP DEFAULT (CURRENT_TIMESTAMP - INTERVAL '5 minutes'),
            next_call TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '5 minutes'),
            tags TEXT[] DEFAULT NULL,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def client_event(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_events (
            client_id VARCHAR(255) NOT NULL,
            event_id VARCHAR(255) PRIMARY KEY NOT NULL,
            event_type VARCHAR(255) NOT NULL,
            occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            injest_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payload JSONB DEFAULT NULL,
            tags TEXT[] DEFAULT NULL,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def client_alert(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_alerts (
            client_id VARCHAR(255),
            alert_id VARCHAR(255) PRIMARY KEY NOT NULL,
            rule_id VARCHAR(255) NOT NULL,
            severity ALERT_SEVERITY DEFAULT 'undefined',
            score INTEGER DEFAULT 0,
            title VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            status ALERT_STATUS DEFAULT 'unresolved',
            payload JSONB DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged BOOLEAN DEFAULT FALSE,
            resolved BOOLEAN DEFAULT FALSE,
            tags TEXT[] DEFAULT NULL,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def client_changes(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_changes (
            client_id VARCHAR(255) NOT NULL,
            change_id VARCHAR(255) PRIMARY KEY NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            change_type VARCHAR(255) NOT NULL, 
            initiated_by VARCHAR(255) NOT NULL,
            previous_state JSONB DEFAULT NULL,
            new_state JSONB DEFAULT NULL,
            status CHANGE_STATUS DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP DEFAULT NULL,
            notes TEXT DEFAULT NULL,
            tags TEXT[] DEFAULT NULL,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        # future notes, look at changing change_type to an enum to enforce consistency.
        # add feature to schedual changes for future implementation.
        cursor.execute(query)

    def client_configs(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_configs (
            client_id VARCHAR(255) NOT NULL,
            CONFIG_ID VARCHAR(255) PRIMARY KEY NOT NULL,
            config JSONB DEFAULT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def server_details(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS server_details (
            server_id VARCHAR(255) PRIMARY KEY NOT NULL,
            public_ip inet default NULL,
            private_ip inet default NULL,
            port INTEGER default NULL,
            hostname VARCHAR(255) default NULL,
            environment VARCHAR(255) default NULL,
            system_info JSONB default NULL,
            uptime_seconds INTEGER default 0,
            agent_count INTEGER default 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cursor.execute(query)

    def auth(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS auth (
            user_id VARCHAR(255) PRIMARY KEY NOT NULL,
            pass_hash VARCHAR(255) NOT NULL
        );
        """

        cursor.execute(query)

    def user_permissions(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id VARCHAR(255) NOT NULL,
            email varchar(255) NOT NULL,
            display_name varchar(255) NOT NULL DEFAULT 'User',
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            roles TEXT[] DEFAULT NULL,
            permissions TEXT[] DEFAULT NULL,

            PRIMARY KEY (user_id, email),
            FOREIGN KEY (user_id) REFERENCES auth(user_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def client_organizations(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS client_organizations (
            client_id VARCHAR(255) PRIMARY KEY NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            group_id VARCHAR(255) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (client_id) REFERENCES registered_clients(client_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """

        cursor.execute(query)

    def notification_integrations(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS notification_integrations (
            integration_id VARCHAR(255) PRIMARY KEY NOT NULL,
            type VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            config JSONB DEFAULT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cursor.execute(query)

    def server_audit_logs(self, cursor):
        query = """
        CREATE TABLE IF NOT EXISTS server_audit_logs (
            audit_id VARCHAR(255) PRIMARY KEY NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            action VARCHAR(255) NOT NULL,
            entity_id VARCHAR(255) DEFAULT NULL,
            entity_type VARCHAR(255) DEFAULT NULL,
            request_ip inet DEFAULT NULL,
            payload JSONB DEFAULT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cursor.execute(query)

if __name__ == "__main__": 
    config = Config()
    config.create_enums()
    config.create_tables()
    config.db.close()
