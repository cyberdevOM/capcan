"""     
client_id VARCHAR(255) PRIMARY KEY NOT NULL,
client_number SERIAL UNIQUE NOT NULL,
hostname VARCHAR(255) NOT NULL,
description TEXT DEFAULT NULL,
registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
revoked BOOLEAN DEFAULT FALSE,
notes TEXT DEFAULT NULL
"""

import uuid
import random
from src.server.core.database import Database 


def gen_clients(n=1000):
    # Return a list of dictionaries representing clients with random data.
    clients = []
    for i in range(n):
        clients.append({
            "client_id": str(uuid.uuid4()),
            "hostname": f"host-{random.randint(1, 1_000_000)}-testing",
            "description": f"Auto-generated client {i}",
            "notes": "This client was generated for testing.",
        })
    return clients


def fill_clients():
    # Generate and insert a batch of clients into registered_clients table.
    database = Database()
    clients = gen_clients() # default to 1000 clients, adjust as needed for testing
    try:
        with database.cursor() as cursor:
            for c in clients:
                cursor.execute(
                    """
                    INSERT INTO registered_clients
                        (client_id, hostname, description, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (client_id) DO NOTHING;
                    """,
                    (c["client_id"], c["hostname"], c["description"], c["notes"]),
                )
        database.conn.commit()
        print(f"Inserted {len(clients)} clients.")
    except Exception as error:
        print(error)
    finally:
        Database.close(database.conn)

if __name__ == "__main__":
    # when run directly, populate the table
    fill_clients()    