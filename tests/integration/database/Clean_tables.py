import psycopg2
from src.server.core.database import Database as database

def clean_tables():
    db = database()
    if db.conn:
        try:
            with db.cursor as cursor:
                select_tables_query = """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """
                cursor.execute(select_tables_query)
                tables = cursor.fetchall()
                for table in tables:
                    clean_table = f"TRUNCATE TABLE {table[0]} CASCADE;"
                    cursor.execute(clean_table)
        except Exception as error:
            print(error)
            if db.conn:
                db.conn.rollback()
            print("Failed to retrieve or clean tables.")
        finally:
            db.close()
    else:
        print("Database connection failed. Cannot clean tables.")

if __name__ == "__main__":
    clean_tables()