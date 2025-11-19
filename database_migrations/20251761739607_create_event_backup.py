import os
import sys
from pathlib import Path
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from app.utils.logger import logger
from dotenv import load_dotenv

# Add parent directory to path for imports
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

load_dotenv()

def get_database_connection():
    """
    Create database connection using environment variables.
    
    Returns:
        connection: MySQL connection object or None if failed
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        logger.info(f"Connected to database: {os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL Database: {e}")
        return None

def check_table_exists(cursor, table_name):
    """
    Check if a table exists in the current database.
    
    Args:
        cursor: MySQL cursor object
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table_name}'
        """)
        return cursor.fetchone()[0] > 0
    except Error as e:
        logger.error(f"Error checking if table exists: {e}")
        return False

def create_events_backup_table():
    """
    Create the events_backup table with all necessary columns and indexes.
    
    This function:
    1. Connects to the database
    2. Checks if the table already exists
    3. Creates the table with proper structure
    4. Adds all necessary indexes for performance
    5. Verifies the table was created successfully
    6. Logs all steps for audit purposes
    
    Returns:
        bool: True if successful, False otherwise
    """
    connection = get_database_connection()
    if not connection:
        logger.error("Failed to connect to database. Please check your environment variables.")
        return False
    
    try:
        logger.info("Starting events_backup table migration")
        
        cursor = connection.cursor()
        table_name = 'events_backup'
        
        # Check if table already exists
        if check_table_exists(cursor, table_name):
            logger.info(f"Table '{table_name}' already exists. Skipping creation.")
            return True
        
        logger.info(f"Creating '{table_name}' table...")
        create_table_sql = """
        CREATE TABLE events_backup (
            id VARCHAR(128) PRIMARY KEY,
            app_name VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            session_id VARCHAR(128) NOT NULL,
            invocation_id VARCHAR(256) NOT NULL,
            author VARCHAR(256) NOT NULL,
            branch VARCHAR(256) DEFAULT NULL,
            timestamp DATETIME NOT NULL,
            content LONGTEXT DEFAULT NULL,
            actions BLOB,
            long_running_tool_ids_json TEXT DEFAULT NULL,
            grounding_metadata LONGTEXT DEFAULT NULL,
            partial TINYINT(1) DEFAULT NULL,
            turn_complete TINYINT(1) DEFAULT NULL,
            error_code VARCHAR(256) DEFAULT NULL,
            error_message VARCHAR(1024) DEFAULT NULL,
            interrupted TINYINT(1) DEFAULT NULL,
            backed_up_at DATETIME NOT NULL,
            INDEX idx_session_id (session_id),
            INDEX idx_backed_up_at (backed_up_at),
            INDEX idx_session_backed_up (session_id, backed_up_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_table_sql)
        connection.commit()
        logger.info(f"Table '{table_name}' created successfully")
        
        # Verify table was created
        if check_table_exists(cursor, table_name):
            logger.info("Migration completed successfully")
            return True
        else:
            logger.error(f"Failed to verify table '{table_name}' creation")
            return False
            
    except Error as e:
        logger.error(f"Error during migration: {e}")
        connection.rollback()
        return False
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def rollback_migration():
    """
    Rollback the migration by dropping the events_backup table.
    
    WARNING: This will delete all backed up event data in the table!
    
    Returns:
        bool: True if successful, False otherwise
    """
    connection = get_database_connection()
    if not connection:
        logger.error("Failed to connect to database. Please check your environment variables.")
        return False
    
    try:
        logger.info("ROLLBACK: Starting to drop events_backup table")
        
        cursor = connection.cursor()
        table_name = 'events_backup'
        
        # Check if table exists
        if not check_table_exists(cursor, table_name):
            logger.info(f"Table '{table_name}' does not exist. Nothing to rollback.")
            return True
        
        # Drop the table
        logger.info(f"Dropping table '{table_name}'...")
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        connection.commit()
        
        # Verify table was dropped
        if not check_table_exists(cursor, table_name):
            logger.info(f"Table '{table_name}' dropped successfully")
            logger.info("Rollback completed successfully")
            return True
        else:
            logger.error(f"Failed to drop table '{table_name}'")
            return False
            
    except Error as e:
        logger.error(f"Error during rollback: {e}")
        connection.rollback()
        return False
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create events_backup table migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Run migration (create table)
        python 20251761739607_create_event_backup.py
        
        # Rollback migration (drop table)
        python 20251761739607_create_event_backup.py --rollback
        """
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration by dropping the events_backup table"
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        # Confirm rollback
        print("\n" + "=" * 80)
        print("WARNING: You are about to DROP the events_backup table!")
        print("This will delete ALL backed up event data.")
        print("=" * 80)
        response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
        
        if response.lower() == 'yes':
            success = rollback_migration()
            sys.exit(0 if success else 1)
        else:
            logger.info("Rollback cancelled.")
            sys.exit(0)
    else:
        # Run migration
        logger.info("Creating events_backup table for event cleanup functionality")
        
        success = create_events_backup_table()
        
        if success:
            logger.info("MIGRATION SUCCESSFUL")
        else:
            logger.error("MIGRATION FAILED")
        
        sys.exit(0 if success else 1)

