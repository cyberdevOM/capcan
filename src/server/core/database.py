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


if __name__ == "__main__":
    db = Database()
    if db.conn:
        print("Database connection test successful.")
    else:
        print("Database connection test failed.")