#!/usr/bin/env python3
"""
Database Migration: Add audit fields (created_by, updated_by) to tables
Migration ID: 003
Created: 2025-01-08
Description: Adds created_by and updated_by fields to companies, agent_mappings, and llm_credentials tables
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.logger import logger

load_dotenv()

def get_database_url():
    """Get database URL from environment variables"""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "kivo_agent_copy")
    
    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def add_audit_fields_to_companies(engine):
    """Add audit fields to companies table"""
    logger.info("Adding audit fields to companies table...")
    
    with engine.connect() as connection:
        try:
            # Check if created_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME = 'created_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'created_by' column to companies table...")
                connection.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN created_by INT NULL,
                    ADD INDEX idx_companies_created_by (created_by),
                    ADD FOREIGN KEY fk_companies_created_by (created_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'created_by' column to companies table")
            else:
                logger.info("⚠️ 'created_by' column already exists in companies table")
            
            # Check if updated_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME = 'updated_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'updated_by' column to companies table...")
                connection.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN updated_by INT NULL,
                    ADD INDEX idx_companies_updated_by (updated_by),
                    ADD FOREIGN KEY fk_companies_updated_by (updated_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'updated_by' column to companies table")
            else:
                logger.info("⚠️ 'updated_by' column already exists in companies table")
                
        except Exception as e:
            logger.error(f"Error adding audit fields to companies table: {e}")
            raise

def add_audit_fields_to_agent_mappings(engine):
    """Add audit fields to agent_mappings table"""
    logger.info("Adding audit fields to agent_mappings table...")
    
    with engine.connect() as connection:
        try:
            # Check if created_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'agent_mappings' 
                AND COLUMN_NAME = 'created_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'created_by' column to agent_mappings table...")
                connection.execute(text("""
                    ALTER TABLE agent_mappings 
                    ADD COLUMN created_by INT NULL,
                    ADD INDEX idx_agent_mappings_created_by (created_by),
                    ADD FOREIGN KEY fk_agent_mappings_created_by (created_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'created_by' column to agent_mappings table")
            else:
                logger.info("⚠️ 'created_by' column already exists in agent_mappings table")
            
            # Check if updated_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'agent_mappings' 
                AND COLUMN_NAME = 'updated_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'updated_by' column to agent_mappings table...")
                connection.execute(text("""
                    ALTER TABLE agent_mappings 
                    ADD COLUMN updated_by INT NULL,
                    ADD INDEX idx_agent_mappings_updated_by (updated_by),
                    ADD FOREIGN KEY fk_agent_mappings_updated_by (updated_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'updated_by' column to agent_mappings table")
            else:
                logger.info("⚠️ 'updated_by' column already exists in agent_mappings table")
                
        except Exception as e:
            logger.error(f"Error adding audit fields to agent_mappings table: {e}")
            raise

def add_audit_fields_to_llm_credentials(engine):
    """Add audit fields to llm_credentials table"""
    logger.info("Adding audit fields to llm_credentials table...")
    
    with engine.connect() as connection:
        try:
            # Check if created_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME = 'created_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'created_by' column to llm_credentials table...")
                connection.execute(text("""
                    ALTER TABLE llm_credentials 
                    ADD COLUMN created_by INT NULL,
                    ADD INDEX idx_llm_credentials_created_by (created_by),
                    ADD FOREIGN KEY fk_llm_credentials_created_by (created_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'created_by' column to llm_credentials table")
            else:
                logger.info("⚠️ 'created_by' column already exists in llm_credentials table")
            
            # Check if updated_by column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME = 'updated_by'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'updated_by' column to llm_credentials table...")
                connection.execute(text("""
                    ALTER TABLE llm_credentials 
                    ADD COLUMN updated_by INT NULL,
                    ADD INDEX idx_llm_credentials_updated_by (updated_by),
                    ADD FOREIGN KEY fk_llm_credentials_updated_by (updated_by) REFERENCES user(id) ON DELETE SET NULL
                """))
                connection.commit()
                logger.info("✅ Added 'updated_by' column to llm_credentials table")
            else:
                logger.info("⚠️ 'updated_by' column already exists in llm_credentials table")
                
        except Exception as e:
            logger.error(f"Error adding audit fields to llm_credentials table: {e}")
            raise

def verify_migration(engine):
    """Verify that all audit fields have been added successfully"""
    logger.info("Verifying migration...")
    
    with engine.connect() as connection:
        try:
            # Verify companies table fields
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME IN ('created_by', 'updated_by')
                ORDER BY COLUMN_NAME
            """))
            
            companies_fields = result.fetchall()
            logger.info(f"Companies table audit fields: {companies_fields}")
            
            # Verify agent_mappings table fields
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'agent_mappings' 
                AND COLUMN_NAME IN ('created_by', 'updated_by')
                ORDER BY COLUMN_NAME
            """))
            
            agent_mappings_fields = result.fetchall()
            logger.info(f"Agent mappings table audit fields: {agent_mappings_fields}")
            
            # Verify llm_credentials table fields
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME IN ('created_by', 'updated_by')
                ORDER BY COLUMN_NAME
            """))
            
            llm_fields = result.fetchall()
            logger.info(f"LLM Credentials table audit fields: {llm_fields}")
            
            # Check if all required fields exist
            expected_fields = {'created_by', 'updated_by'}
            
            actual_companies_fields = {row[0] for row in companies_fields}
            actual_agent_mappings_fields = {row[0] for row in agent_mappings_fields}
            actual_llm_fields = {row[0] for row in llm_fields}
            
            success = True
            
            if expected_fields.issubset(actual_companies_fields):
                logger.info("✅ All companies table audit fields successfully added")
            else:
                missing = expected_fields - actual_companies_fields
                logger.error(f"❌ Missing companies table audit fields: {missing}")
                success = False
            
            if expected_fields.issubset(actual_agent_mappings_fields):
                logger.info("✅ All agent_mappings table audit fields successfully added")
            else:
                missing = expected_fields - actual_agent_mappings_fields
                logger.error(f"❌ Missing agent_mappings table audit fields: {missing}")
                success = False
            
            if expected_fields.issubset(actual_llm_fields):
                logger.info("✅ All llm_credentials table audit fields successfully added")
            else:
                missing = expected_fields - actual_llm_fields
                logger.error(f"❌ Missing llm_credentials table audit fields: {missing}")
                success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return False

def run_migration():
    """Run the complete migration"""
    logger.info("=" * 60)
    logger.info("Running Database Migration 003: Add Audit Fields")
    logger.info("=" * 60)
    
    try:
        # Create database engine
        database_url = get_database_url()
        logger.info(f"Connecting to database...")
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE() as db_name"))
            db_name = result.fetchone()[0]
            logger.info(f"✅ Connected to database: {db_name}")
        
        # Run migrations
        add_audit_fields_to_companies(engine)
        add_audit_fields_to_agent_mappings(engine)
        add_audit_fields_to_llm_credentials(engine)
        
        # Verify migration
        if verify_migration(engine):
            logger.info("=" * 60)
            logger.info("🎉 Migration 003 completed successfully!")
            logger.info("=" * 60)
            logger.info("Added audit fields to tables:")
            logger.info("📋 Companies table:")
            logger.info("   - created_by (INT, nullable, indexed, FK to user.id)")
            logger.info("   - updated_by (INT, nullable, indexed, FK to user.id)")
            logger.info("🔗 Agent Mappings table:")
            logger.info("   - created_by (INT, nullable, indexed, FK to user.id)")
            logger.info("   - updated_by (INT, nullable, indexed, FK to user.id)")
            logger.info("🔑 LLM Credentials table:")
            logger.info("   - created_by (INT, nullable, indexed, FK to user.id)")
            logger.info("   - updated_by (INT, nullable, indexed, FK to user.id)")
            logger.info("=" * 60)
            return True
        else:
            logger.error("❌ Migration verification failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration 003 failed: {e}")
        return False

def rollback_migration():
    """Rollback the migration (remove added audit fields)"""
    logger.info("=" * 60)
    logger.info("Rolling back Database Migration 003")
    logger.info("=" * 60)
    
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Remove companies table audit fields
            logger.info("Removing audit fields from companies table...")
            try:
                connection.execute(text("ALTER TABLE companies DROP FOREIGN KEY fk_companies_created_by"))
                connection.execute(text("ALTER TABLE companies DROP FOREIGN KEY fk_companies_updated_by"))
                connection.execute(text("ALTER TABLE companies DROP COLUMN created_by"))
                connection.execute(text("ALTER TABLE companies DROP COLUMN updated_by"))
                connection.commit()
                logger.info("✅ Removed companies table audit fields")
            except Exception as e:
                logger.warning(f"⚠️ Error removing companies audit fields (may not exist): {e}")
            
            # Remove agent_mappings table audit fields
            logger.info("Removing audit fields from agent_mappings table...")
            try:
                connection.execute(text("ALTER TABLE agent_mappings DROP FOREIGN KEY fk_agent_mappings_created_by"))
                connection.execute(text("ALTER TABLE agent_mappings DROP FOREIGN KEY fk_agent_mappings_updated_by"))
                connection.execute(text("ALTER TABLE agent_mappings DROP COLUMN created_by"))
                connection.execute(text("ALTER TABLE agent_mappings DROP COLUMN updated_by"))
                connection.commit()
                logger.info("✅ Removed agent_mappings table audit fields")
            except Exception as e:
                logger.warning(f"⚠️ Error removing agent_mappings audit fields (may not exist): {e}")
            
            # Remove llm_credentials table audit fields
            logger.info("Removing audit fields from llm_credentials table...")
            try:
                connection.execute(text("ALTER TABLE llm_credentials DROP FOREIGN KEY fk_llm_credentials_created_by"))
                connection.execute(text("ALTER TABLE llm_credentials DROP FOREIGN KEY fk_llm_credentials_updated_by"))
                connection.execute(text("ALTER TABLE llm_credentials DROP COLUMN created_by"))
                connection.execute(text("ALTER TABLE llm_credentials DROP COLUMN updated_by"))
                connection.commit()
                logger.info("✅ Removed llm_credentials table audit fields")
            except Exception as e:
                logger.warning(f"⚠️ Error removing llm_credentials audit fields (may not exist): {e}")
        
        logger.info("🔄 Migration 003 rollback completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration 003: Add Audit Fields")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--verify", action="store_true", help="Only verify the migration")
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    elif args.verify:
        database_url = get_database_url()
        engine = create_engine(database_url)
        success = verify_migration(engine)
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
