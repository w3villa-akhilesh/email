#!/usr/bin/env python3
"""
Database migration script to add app_name column to iats_user_sessions table.
This fixes the error: Unknown column 'iats_user_sessions.app_name' in 'field list'
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """Create database connection using environment variables"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in the table"""
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

def migrate_app_name_column():
    """Add app_name column to iats_user_sessions table if it doesn't exist"""
    connection = get_database_connection()
    if not connection:
        print("Failed to connect to database. Please check your environment variables.")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if app_name column already exists
        if check_column_exists(cursor, 'iats_user_sessions', 'app_name'):
            print("Column 'app_name' already exists in 'iats_user_sessions' table.")
            return True
        
        # Add the app_name column
        print("Adding 'app_name' column to 'iats_user_sessions' table...")
        cursor.execute("""
            ALTER TABLE iats_user_sessions 
            ADD COLUMN app_name VARCHAR(255) NULL
        """)
        
        # Add index for better performance
        print("Adding index on 'app_name' column...")
        cursor.execute("""
            CREATE INDEX idx_iats_user_sessions_app_name 
            ON iats_user_sessions(app_name)
        """)
        
        # Update existing records to have 'iats_sequential_flow' as the default app_name
        print("Updating existing records with default app_name 'iats_sequential_flow'...")
        cursor.execute("""
            UPDATE iats_user_sessions 
            SET app_name = 'iats_sequential_flow' 
            WHERE app_name IS NULL
        """)
        
        # Commit the changes
        connection.commit()
        print("Successfully added 'app_name' column, index, and updated existing records in 'iats_user_sessions' table.")
        
        # Verify the column was added
        cursor.execute("DESCRIBE iats_user_sessions")
        columns = cursor.fetchall()
        print("\nTable structure after migration:")
        for column in columns:
            print(f"  {column[0]} - {column[1]}")
        
        return True
        
    except Error as e:
        print(f"Error during migration: {e}")
        connection.rollback()
        return False
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    print("Starting database migration for app_name column...")
    success = migrate_app_name_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The 'app_name' column has been added to the 'iats_user_sessions' table.")
        print("You can now run your application without the column error.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
