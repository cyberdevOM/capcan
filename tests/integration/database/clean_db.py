import psycopg2
from src.server.core.database import Database

def clean_db():
    db = Database()
    if db.conn:
        try:
            with db.conn.cursor() as cursor:
                get_tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """
                cursor.execute(get_tables_query)
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"TRUNCATE TABLE {table[0]} CASCADE;")
            db.conn.commit()
            print("Database cleaned successfully.")
        except Exception as error:
            print(error)
            db.conn.rollback()
        finally:
            db.close()
            
def drop_tables():
    db = Database()
    if db.conn:
        try:
            with db.conn.cursor() as cursor:
                get_tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """
                cursor.execute(get_tables_query)
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]} CASCADE;")
            db.conn.commit()
            print("All tables dropped successfully.")
        except Exception as error:
            print(error)
            db.conn.rollback()
        finally:
            db.close()
            
if __name__ == "__main__":
    # when run directly, clean the database
    #clean_db()
    drop_tables()