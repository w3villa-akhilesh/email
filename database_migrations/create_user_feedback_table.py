"""
Database Migration Script: Create user_feedback Table

This script creates the user_feedback table for storing message-level
thumbs up/down feedback with context (company, origin, session).

Usage:
    python create_user_feedback_table.py

The script will:
1. Check if the table already exists
2. Create the table if it doesn't exist
3. Add necessary indexes (defined in the model)
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
from sqlalchemy import create_engine, inspect
from app.models.db_models import UserFeedback
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

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME")

    db_password_encoded = quote_plus(db_password)
    return f"mysql+mysqlconnector://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"


def check_table_exists(engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_user_feedback_table() -> bool:
    try:
        logger.info("=" * 80)
        logger.info("Starting user_feedback table migration")
        logger.info(f"Migration started at: {datetime.utcnow().isoformat()}")
        logger.info("=" * 80)

        database_url = get_database_url()
        logger.info(f"Connecting to database: {os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")

        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=10,
        )

        table_name = "user_feedback"
        if check_table_exists(engine, table_name):
            logger.warning(f"Table '{table_name}' already exists. Skipping creation.")
            logger.info("=" * 80)
            logger.info("Migration completed (table already exists)")
            logger.info("=" * 80)
            return True

        logger.info(f"Table '{table_name}' does not exist. Proceeding with creation.")
        logger.info("Creating user_feedback table...")
        UserFeedback.__table__.create(engine)

        if check_table_exists(engine, table_name):
            logger.info(f"\u2713 Table '{table_name}' created successfully")
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)

            logger.info(f"\u2713 Table has {len(columns)} columns")
            logger.info(f"\u2713 Table has {len(indexes)} indexes")

            logger.info("\nTable columns:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

            logger.info("\nTable indexes:")
            for idx in indexes:
                logger.info(f"  - {idx['name']}: columns={idx['column_names']}, unique={idx['unique']}")

            logger.info("=" * 80)
            logger.info("Migration completed successfully")
            logger.info(f"Migration ended at: {datetime.utcnow().isoformat()}")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"\u2717 Failed to create table '{table_name}'")
            return False

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        logger.error("Migration failed")
        logger.error("=" * 80)
        return False


def rollback_migration() -> bool:
    try:
        logger.warning("=" * 80)
        logger.warning("ROLLBACK: Starting to drop user_feedback table")
        logger.warning("WARNING: This will delete all data in the table!")
        logger.warning("=" * 80)

        database_url = get_database_url()
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=10,
        )

        table_name = "user_feedback"
        if not check_table_exists(engine, table_name):
            logger.info(f"Table '{table_name}' does not exist. Nothing to rollback.")
            return True

        logger.info(f"Dropping table '{table_name}'...")
        UserFeedback.__table__.drop(engine)

        if not check_table_exists(engine, table_name):
            logger.info(f"\u2713 Table '{table_name}' dropped successfully")
            logger.info("=" * 80)
            logger.info("Rollback completed successfully")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"\u2717 Failed to drop table '{table_name}'")
            return False

    except Exception as e:
        logger.error(f"Error during rollback: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        logger.error("Rollback failed")
        logger.error("=" * 80)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create user_feedback table migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration by dropping the table")

    args = parser.parse_args()

    if args.rollback:
        print("\n" + "=" * 80)
        print("WARNING: You are about to DROP the user_feedback table!")
        print("This will delete ALL user feedback data.")
        print("=" * 80)
        response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
        if response.lower() == "yes":
            success = rollback_migration()
            sys.exit(0 if success else 1)
        else:
            print("Rollback cancelled.")
            sys.exit(0)
    else:
        success = create_user_feedback_table()
        sys.exit(0 if success else 1)
