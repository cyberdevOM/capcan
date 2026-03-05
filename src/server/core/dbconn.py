import psycopg2
import os
from dotenv import load_dotenv as load_env

#   __summary__
#   Establishes a connection to the PostgreSQL database.
#   Returns:
#       A connection object if successful, None otherwise.

def connect():
    load_env()
    try:
        with psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        ) as conn:
            print ("Database connection established.")
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)
        return None
    
def close(conn):
    if conn:
        conn.close()
        print("Database connection closed.")
    
if __name__ == "__main__":
    conn = connect()
    close(conn)