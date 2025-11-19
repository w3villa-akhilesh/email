"""
Database Migration Script: Create network_activity_logs Table

This script creates the network_activity_logs table for storing network activity
and security monitoring data. It can be run standalone or as part of a migration process.

Usage:
    python create_network_activity_logs_table.py

The script will:
1. Check if the table already exists
2. Create the table if it doesn't exist
3. Add all necessary indexes for performance
4. Provide detailed logging of the migration process
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Base, NetworkActivityLog
from app.utils.logger import logger

# Load environment variables
load_dotenv()


def get_database_url():
    """
    Construct database URL from environment variables.
    
    Returns:
        str: Database connection URL
    """
    from urllib.parse import quote_plus
    
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME")
    
    if not all([db_user, db_password, db_name]):
        raise ValueError("Missing required database environment variables: DB_USER, DB_PASSWORD, DB_NAME")
    
    db_password_encoded = quote_plus(db_password)
    return f"mysql+mysqlconnector://{db_user}:{db_password_encoded}@{db_host}/{db_name}"


def check_table_exists(engine, table_name):
    """
    Check if a table exists in the database.
    
    Args:
        engine: SQLAlchemy engine instance
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_network_activity_logs_table():
    """
    Create the network_activity_logs table and its indexes.
    
    This function:
    1. Connects to the database
    2. Checks if the table already exists
    3. Creates the table using SQLAlchemy models
    4. Verifies the table was created successfully
    5. Logs all steps for audit purposes
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting network_activity_logs table migration")
        logger.info(f"Migration started at: {datetime.utcnow().isoformat()}")
        logger.info("=" * 80)
        
        # Get database URL
        database_url = get_database_url()
        logger.info(f"Connecting to database: {os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
        
        # Create engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=10
        )
        
        # Check if table already exists
        table_name = "network_activity_logs"
        if check_table_exists(engine, table_name):
            logger.warning(f"Table '{table_name}' already exists. Skipping creation.")
            logger.info("=" * 80)
            logger.info("Migration completed (table already exists)")
            logger.info("=" * 80)
            return True
        
        logger.info(f"Table '{table_name}' does not exist. Proceeding with creation.")
        
        # Create the table using SQLAlchemy models
        logger.info("Creating network_activity_logs table...")
        NetworkActivityLog.__table__.create(engine)
        
        # Verify table was created
        if check_table_exists(engine, table_name):
            logger.info(f"✓ Table '{table_name}' created successfully")
            
            # Get table info
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            
            logger.info(f"✓ Table has {len(columns)} columns")
            logger.info(f"✓ Table has {len(indexes)} indexes")
            
            # Log column details
            logger.info("\nTable columns:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")
            
            # Log index details
            logger.info("\nTable indexes:")
            for idx in indexes:
                logger.info(f"  - {idx['name']}: columns={idx['column_names']}, unique={idx['unique']}")
            
            logger.info("=" * 80)
            logger.info("Migration completed successfully")
            logger.info(f"Migration ended at: {datetime.utcnow().isoformat()}")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"✗ Failed to create table '{table_name}'")
            return False
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        logger.error("Migration failed")
        logger.error("=" * 80)
        return False


def rollback_migration():
    """
    Rollback the migration by dropping the network_activity_logs table.
    
    WARNING: This will delete all data in the table!
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.warning("=" * 80)
        logger.warning("ROLLBACK: Starting to drop network_activity_logs table")
        logger.warning("WARNING: This will delete all data in the table!")
        logger.warning("=" * 80)
        
        # Get database URL
        database_url = get_database_url()
        
        # Create engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=10
        )
        
        # Check if table exists
        table_name = "network_activity_logs"
        if not check_table_exists(engine, table_name):
            logger.info(f"Table '{table_name}' does not exist. Nothing to rollback.")
            return True
        
        # Drop the table
        logger.info(f"Dropping table '{table_name}'...")
        NetworkActivityLog.__table__.drop(engine)
        
        # Verify table was dropped
        if not check_table_exists(engine, table_name):
            logger.info(f"✓ Table '{table_name}' dropped successfully")
            logger.info("=" * 80)
            logger.info("Rollback completed successfully")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"✗ Failed to drop table '{table_name}'")
            return False
            
    except Exception as e:
        logger.error(f"Error during rollback: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        logger.error("Rollback failed")
        logger.error("=" * 80)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create network_activity_logs table migration"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration by dropping the table"
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        # Confirm rollback
        print("\n" + "=" * 80)
        print("WARNING: You are about to DROP the network_activity_logs table!")
        print("This will delete ALL network activity log data.")
        print("=" * 80)
        response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
        
        if response.lower() == 'yes':
            success = rollback_migration()
            sys.exit(0 if success else 1)
        else:
            print("Rollback cancelled.")
            sys.exit(0)
    else:
        # Run migration
        success = create_network_activity_logs_table()
        sys.exit(0 if success else 1)

