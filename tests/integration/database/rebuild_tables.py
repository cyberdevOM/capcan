from src.server.core.database import Database
from src.server.core.config import Config

def get_tables():
    db = Database()
    try:
        db.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = db.cursor.fetchall()
        return [table[0] for table in tables]
    except Exception as e:
        print(f"Error fetching tables: {e}")
        return []
    finally:
        db.close()

def rebuild_tables():
    db = Database()
    try:
        for table in get_tables():
            db.cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        db.conn.commit()
        print("All tables dropped successfully.")
    except Exception as e:
        print(f"Error dropping tables: {e}")
    finally:
        db.close()

    Config().create_enums()
    Config().create_tables()
    print("Tables recreated successfully.")

if __name__ == "__main__":
    rebuild_tables()