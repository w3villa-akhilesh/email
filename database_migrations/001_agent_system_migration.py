#!/usr/bin/env python3
"""
Consolidated Agent System Migration

This migration creates the complete multi-company, multi-agent system:
1. Creates companies table
2. Creates agents table with parent-child relationships
3. Modifies llm_credentials table to be company-specific
4. Creates agent_mappings table for company-agent associations
5. Adds selected_model field to agent_mappings

Usage:
    python 001_agent_system_migration.py
    python 001_agent_system_migration.py --rollback
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.services.my_sql_client import get_db
from app.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

def execute_sql_statements(db, statements, description):
    """Execute a list of SQL statements with error handling"""
    for i, statement in enumerate(statements):
        try:
            logger.info(f"{description} - Executing statement {i+1}/{len(statements)}")
            db.execute(text(statement))
            logger.debug(f"Successfully executed: {statement[:100]}...")
        except Exception as e:
            # Check if it's a "column already exists" or "column doesn't exist" error
            error_msg = str(e).lower()
            if any(phrase in error_msg for phrase in ["duplicate column", "column already exists", "unknown column", "can't drop"]):
                logger.info(f"Skipping statement (expected): {e}")
            else:
                logger.warning(f"Statement failed (continuing): {e}")
            logger.debug(f"Failed statement: {statement}")

def create_companies_table(db):
    """Create companies table"""
    logger.info("Creating companies table...")
    
    statements = [
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            origin VARCHAR(255) NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            
            INDEX idx_companies_name (name),
            INDEX idx_companies_origin (origin),
            INDEX idx_companies_active (is_active)
        )
        """
    ]
    
    execute_sql_statements(db, statements, "Creating companies table")

def create_agents_table(db):
    """Create agents table with parent-child relationships"""
    logger.info("Creating agents table...")
    
    statements = [
        """
        CREATE TABLE IF NOT EXISTS agents (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            parent_agent_id INT DEFAULT NULL,
            agent_type VARCHAR(20) DEFAULT 'primary',
            default_model VARCHAR(100) DEFAULT NULL,
            system_prompt TEXT DEFAULT NULL,
            capabilities JSON DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            FOREIGN KEY (parent_agent_id) REFERENCES agents(id) ON DELETE SET NULL,
            INDEX idx_agents_name (name),
            INDEX idx_agents_parent (parent_agent_id),
            INDEX idx_agents_type (agent_type),
            INDEX idx_agents_active (is_active)
        )
        """
    ]
    
    execute_sql_statements(db, statements, "Creating agents table")

def modify_llm_credentials_table(db):
    """Modify existing llm_credentials table to be company-specific"""
    logger.info("Modifying llm_credentials table...")
    
    # First, backup existing data if needed
    backup_statements = [
        """
        CREATE TABLE IF NOT EXISTS llm_credentials_backup AS 
        SELECT * FROM llm_credentials LIMIT 0
        """,
        """
        INSERT IGNORE INTO llm_credentials_backup 
        SELECT * FROM llm_credentials
        """
    ]
    
    # Step-by-step table modification (MySQL compatible)
    modification_statements = [
        # Add new columns first (check if they exist first)
        "ALTER TABLE llm_credentials ADD COLUMN provider VARCHAR(100) NOT NULL DEFAULT 'openai'",
        "ALTER TABLE llm_credentials ADD COLUMN available_models JSON",
        "ALTER TABLE llm_credentials ADD COLUMN is_default BOOLEAN DEFAULT FALSE",
        "ALTER TABLE llm_credentials ADD COLUMN max_tokens INT DEFAULT NULL",
        "ALTER TABLE llm_credentials ADD COLUMN temperature VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE llm_credentials ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
        
        # Rename existing columns (if they exist)
        "ALTER TABLE llm_credentials CHANGE COLUMN llm_key api_key VARCHAR(512) NOT NULL",
        "ALTER TABLE llm_credentials CHANGE COLUMN llm_base_url base_url VARCHAR(255) NOT NULL",
        
        # Modify company_id to be proper foreign key
        "ALTER TABLE llm_credentials MODIFY COLUMN company_id INT NOT NULL",
        
        # Add indexes first (before foreign key)
        "CREATE INDEX idx_llm_credentials_company ON llm_credentials(company_id)",
        "CREATE INDEX idx_llm_credentials_provider ON llm_credentials(provider)",
        "CREATE INDEX idx_llm_credentials_active ON llm_credentials(is_active)",
        "CREATE INDEX idx_llm_credentials_default ON llm_credentials(is_default)",
        
        # Add foreign key constraint
        """
        ALTER TABLE llm_credentials 
        ADD CONSTRAINT fk_llm_credentials_company 
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        """,
    ]
    
    # Drop old columns (MySQL doesn't support IF EXISTS in ALTER TABLE)
    cleanup_statements = [
        "ALTER TABLE llm_credentials DROP COLUMN llm_model",
        "ALTER TABLE llm_credentials DROP COLUMN app_name", 
        "ALTER TABLE llm_credentials DROP COLUMN origin",
    ]
    
    execute_sql_statements(db, backup_statements, "Backing up llm_credentials")
    execute_sql_statements(db, modification_statements, "Modifying llm_credentials table")
    execute_sql_statements(db, cleanup_statements, "Cleaning up old columns")

def create_agent_mappings_table(db):
    """Create agent_mappings table with selected_model field"""
    logger.info("Creating agent_mappings table...")
    
    statements = [
        """
        CREATE TABLE IF NOT EXISTS agent_mappings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            company_id INT NOT NULL,
            agent_id INT NOT NULL,
            llm_credentials_id INT NOT NULL,
            preferred_model VARCHAR(100) DEFAULT NULL,
            selected_model VARCHAR(100) DEFAULT NULL,
            custom_system_prompt TEXT DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            priority INT DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
            FOREIGN KEY (llm_credentials_id) REFERENCES llm_credentials(id) ON DELETE CASCADE,
            
            UNIQUE KEY idx_company_agent_unique (company_id, agent_id),
            INDEX idx_agent_mappings_company (company_id),
            INDEX idx_agent_mappings_agent (agent_id),
            INDEX idx_agent_mappings_credentials (llm_credentials_id),
            INDEX idx_agent_mappings_active (is_active),
            INDEX idx_company_agent_active (company_id, agent_id, is_active),
            INDEX idx_company_credentials (company_id, llm_credentials_id),
            INDEX idx_agent_mappings_selected_model (selected_model)
        )
        """
    ]
    
    execute_sql_statements(db, statements, "Creating agent_mappings table")

def run_migration():
    """Run the complete migration"""
    db = next(get_db())
    
    try:
        logger.info("Starting consolidated agent system migration...")
        
        # Create all tables and modifications
        create_companies_table(db)
        create_agents_table(db)
        modify_llm_credentials_table(db)
        create_agent_mappings_table(db)
        
        # Commit all changes
        db.commit()
        logger.info("Migration completed successfully!")
        
        # Show final table structures
        logger.info("Final table structures:")
        for table in ['companies', 'agents', 'llm_credentials', 'agent_mappings']:
            try:
                result = db.execute(text(f"DESCRIBE {table}"))
                logger.info(f"\n{table.upper()} table structure:")
                for row in result.fetchall():
                    logger.info(f"  {row}")
            except Exception as e:
                logger.warning(f"Could not describe {table}: {e}")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def rollback_migration():
    """Rollback the migration"""
    db = next(get_db())
    
    try:
        logger.info("Rolling back agent system migration...")
        
        # Drop tables in reverse order
        rollback_statements = [
            "DROP TABLE IF EXISTS agent_mappings",
            "DROP TABLE IF EXISTS agents",
            # Note: We don't drop companies or completely revert llm_credentials 
            # as they might have important data
            "DROP TABLE IF EXISTS llm_credentials_backup",
        ]
        
        execute_sql_statements(db, rollback_statements, "Rolling back migration")
        
        db.commit()
        logger.info("Rollback completed successfully!")
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run consolidated agent system migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    
    args = parser.parse_args()
    
    try:
        if args.rollback:
            rollback_migration()
        else:
            run_migration()
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)
