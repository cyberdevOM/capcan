import psycopg2
from src.server.core.database import Database as database

def drop_tables():
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
                    drop_query = f"DROP TABLE IF EXISTS {table[0]} CASCADE;"
                    try: 
                        cursor.execute(drop_query)
                        print(f"Table '{table[0]}' dropped successfully.")
                    except psycopg2.Error as error:
                        print(f"Error occurred while dropping table '{table[0]}': {error}")
                print("Tables dropped successfully.")
        except Exception as error:
            print(error)
            if db.conn:
                db.conn.rollback()
            print("Failed to retrieve or drop tables.")
        finally:
            db.close()
    else:
        print("Database connection failed. Cannot drop tables.")

if __name__ == "__main__":
    drop_tables()