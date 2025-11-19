#!/usr/bin/env python3
"""
Database Migration: Add new fields to companies and llm_credentials tables
Migration ID: 002
Created: 2025-01-XX
Description: Adds description and company_id to companies table, and CRM-related fields to llm_credentials table
"""

import os
import sys
from sqlalchemy import create_engine, text, Column, String, Boolean, Text
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

def add_company_fields(engine):
    """Add new fields to companies table"""
    logger.info("Adding new fields to companies table...")
    
    with engine.connect() as connection:
        try:
            # Check if description column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME = 'description'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'description' column to companies table...")
                connection.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN description TEXT NULL
                """))
                connection.commit()
                logger.info("✅ Added 'description' column to companies table")
            else:
                logger.info("⚠️ 'description' column already exists in companies table")
            
            # Check if company_id column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME = 'company_id'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'company_id' column to companies table...")
                connection.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN company_id VARCHAR(100) NULL,
                    ADD INDEX idx_companies_company_id (company_id)
                """))
                connection.commit()
                logger.info("✅ Added 'company_id' column to companies table")
            else:
                logger.info("⚠️ 'company_id' column already exists in companies table")
                
        except Exception as e:
            logger.error(f"Error adding fields to companies table: {e}")
            raise

def add_llm_credentials_fields(engine):
    """Add new fields to llm_credentials table"""
    logger.info("Adding new fields to llm_credentials table...")
    
    with engine.connect() as connection:
        try:
            # Check if is_crm_flow_active column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME = 'is_crm_flow_active'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'is_crm_flow_active' column to llm_credentials table...")
                connection.execute(text("""
                    ALTER TABLE llm_credentials 
                    ADD COLUMN is_crm_flow_active BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD INDEX idx_llm_credentials_crm_flow (is_crm_flow_active)
                """))
                connection.commit()
                logger.info("✅ Added 'is_crm_flow_active' column to llm_credentials table")
            else:
                logger.info("⚠️ 'is_crm_flow_active' column already exists in llm_credentials table")
            
            # Check if crm_accounts_ids column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME = 'crm_accounts_ids'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'crm_accounts_ids' column to llm_credentials table...")
                connection.execute(text("""
                    ALTER TABLE llm_credentials 
                    ADD COLUMN crm_accounts_ids VARCHAR(1000) NULL
                """))
                connection.commit()
                logger.info("✅ Added 'crm_accounts_ids' column to llm_credentials table")
            else:
                logger.info("⚠️ 'crm_accounts_ids' column already exists in llm_credentials table")
            
            # Check if tags column exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME = 'tags'
            """))
            
            if result.fetchone()[0] == 0:
                logger.info("Adding 'tags' column to llm_credentials table...")
                connection.execute(text("""
                    ALTER TABLE llm_credentials 
                    ADD COLUMN tags VARCHAR(500) NULL
                """))
                connection.commit()
                logger.info("✅ Added 'tags' column to llm_credentials table")
            else:
                logger.info("⚠️ 'tags' column already exists in llm_credentials table")
                
        except Exception as e:
            logger.error(f"Error adding fields to llm_credentials table: {e}")
            raise

def verify_migration(engine):
    """Verify that all new fields have been added successfully"""
    logger.info("Verifying migration...")
    
    with engine.connect() as connection:
        try:
            # Verify companies table fields
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'companies' 
                AND COLUMN_NAME IN ('description', 'company_id')
                ORDER BY COLUMN_NAME
            """))
            
            companies_fields = result.fetchall()
            logger.info(f"Companies table new fields: {companies_fields}")
            
            # Verify llm_credentials table fields
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'llm_credentials' 
                AND COLUMN_NAME IN ('is_crm_flow_active', 'crm_accounts_ids', 'tags')
                ORDER BY COLUMN_NAME
            """))
            
            llm_fields = result.fetchall()
            logger.info(f"LLM Credentials table new fields: {llm_fields}")
            
            # Check if all required fields exist
            expected_companies_fields = {'description', 'company_id'}
            expected_llm_fields = {'is_crm_flow_active', 'crm_accounts_ids', 'tags'}
            
            actual_companies_fields = {row[0] for row in companies_fields}
            actual_llm_fields = {row[0] for row in llm_fields}
            
            if expected_companies_fields.issubset(actual_companies_fields):
                logger.info("✅ All companies table fields successfully added")
            else:
                missing = expected_companies_fields - actual_companies_fields
                logger.error(f"❌ Missing companies table fields: {missing}")
                return False
            
            if expected_llm_fields.issubset(actual_llm_fields):
                logger.info("✅ All llm_credentials table fields successfully added")
            else:
                missing = expected_llm_fields - actual_llm_fields
                logger.error(f"❌ Missing llm_credentials table fields: {missing}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return False

def run_migration():
    """Run the complete migration"""
    logger.info("=" * 60)
    logger.info("Running Database Migration 002: Add Company and LLM Fields")
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
        add_company_fields(engine)
        add_llm_credentials_fields(engine)
        
        # Verify migration
        if verify_migration(engine):
            logger.info("=" * 60)
            logger.info("🎉 Migration 002 completed successfully!")
            logger.info("=" * 60)
            logger.info("Added fields:")
            logger.info("📋 Companies table:")
            logger.info("   - description (TEXT, nullable)")
            logger.info("   - company_id (VARCHAR(100), nullable, indexed)")
            logger.info("🔑 LLM Credentials table:")
            logger.info("   - is_crm_flow_active (BOOLEAN, default: FALSE, indexed)")
            logger.info("   - crm_accounts_ids (VARCHAR(1000), nullable)")
            logger.info("   - tags (VARCHAR(500), nullable)")
            logger.info("=" * 60)
            return True
        else:
            logger.error("❌ Migration verification failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration 002 failed: {e}")
        return False

def rollback_migration():
    """Rollback the migration (remove added fields)"""
    logger.info("=" * 60)
    logger.info("Rolling back Database Migration 002")
    logger.info("=" * 60)
    
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Remove companies table fields
            logger.info("Removing fields from companies table...")
            try:
                connection.execute(text("ALTER TABLE companies DROP COLUMN description"))
                connection.execute(text("ALTER TABLE companies DROP COLUMN company_id"))
                connection.commit()
                logger.info("✅ Removed companies table fields")
            except Exception as e:
                logger.warning(f"⚠️ Error removing companies fields (may not exist): {e}")
            
            # Remove llm_credentials table fields
            logger.info("Removing fields from llm_credentials table...")
            try:
                connection.execute(text("ALTER TABLE llm_credentials DROP COLUMN is_crm_flow_active"))
                connection.execute(text("ALTER TABLE llm_credentials DROP COLUMN crm_accounts_ids"))
                connection.execute(text("ALTER TABLE llm_credentials DROP COLUMN tags"))
                connection.commit()
                logger.info("✅ Removed llm_credentials table fields")
            except Exception as e:
                logger.warning(f"⚠️ Error removing llm_credentials fields (may not exist): {e}")
        
        logger.info("🔄 Migration 002 rollback completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration 002: Add Company and LLM Fields")
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
