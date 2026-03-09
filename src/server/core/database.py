import psycopg2
import os
from dotenv import load_dotenv as load_env
from enum import Enum

class Database:
    def __init__(self):
        load_env()
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("BD_HOST"),
                database=os.getenv("DB_NAME"),
                port=os.getenv("DB_PORT"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            print ("Database connection established.")
            return self.conn
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            self.conn = None
            
    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
            
    def create_web_user(self, username, hash):
        try:    
            self.conn.cursor().execute(
                "INSERT INTO web_users (username, hash) VALUES (%s, %s);",
                (username, hash)        
            )
            self.conn.commit()
            print(f"Web user '{username}' created successfully.")
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)
            self.conn.rollback()
            print(f"Failed to create web user '{username}'.")


if __name__ == "__main__":
    db = Database()
    if db.conn:
        print("Database connection test successful.")
        db.close()
    else:
        print("Database connection test failed.")