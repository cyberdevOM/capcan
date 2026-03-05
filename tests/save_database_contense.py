import os
from src.server.core.dbconn import connect, close
from psycopg2 import sql

def select_all_tables():
    """Return count and names of all tables in the public schema."""
    conn = connect()
    tables = []
    try:
        save_dir = create_save_location()
        print(f"Save directory created at: {save_dir}")
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
            ) # get all table names in public schema
            tables = cursor.fetchall() # list of tuples like [('registered_clients',), ('client_telemetry',), ...]
            for table in tables:
                tblname = table[0]
                # safely query every row from the table
                cursor.execute(sql.SQL("SELECT * FROM {};").format(sql.Identifier(tblname)))
                rows = cursor.fetchall()
                # build text including column headers
                cols = [desc.name for desc in cursor.description]
                lines = []
                if cols:
                    lines.append(", ".join(cols))
                lines.extend([", ".join(map(str, row)) for row in rows])
                data = "\n".join(lines)
                filename = f"{tblname}.txt"  # extension for clarity
                save_to_file(filename=filename, save_dir=save_dir, data=data)
                print(f"Saved content of {tblname} to {filename}.")
    except Exception as error:
        print(f"Error querying tables: {error}")
    finally:
        close(conn)
    return tables

def save_to_file(filename="database_dump.sql", save_dir=None, data=None):
    """Write ``data`` into ``save_dir/filename``.

    Caller is responsible for creating the directory ahead of time.
    """
    try:
        full_path = os.path.join(save_dir, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(data or "")
        print(f"Database content saved to {filename}")
    except Exception as error:
        print(f"Error saving to file: {error}")
        
def create_save_location():
    # Create dir for saving dumps if it doen't exist.
    base = os.path.dirname(__file__)
    print(f"Base directory for saves: {base}")
    save_dir = os.path.join(base, "db_saves")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    return save_dir

if __name__ == "__main__":
    select_all_tables()