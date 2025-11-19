#!/usr/bin/env python3
"""
Safe script to add only 4 new agents to the database
Does NOT touch agent_mappings or any other data

Usage:
    python add_4_agents_only.py
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

# The 4 new agents to add
NEW_AGENTS = [
    {
        "name": "attendance_agent",
        "display_name": "Attendance Agent",
        "description": "Handles employee attendance tracking, leave requests, absence reports, and attendance summaries",
        "parent_agent_name": "triage_agent",
        "agent_type": "sub_agent",
        "default_model": "gpt-4o",
        "is_active": True
    },
    {
        "name": "payroll_agent",
        "display_name": "Payroll Agent",
        "description": "Manages payroll operations including salary processing, payslip generation, and payroll reports",
        "parent_agent_name": "triage_agent",
        "agent_type": "sub_agent",
        "default_model": "gpt-4o",
        "is_active": True
    },
    {
        "name": "recruiting_agent",
        "display_name": "Recruiting Agent",
        "description": "Handles recruitment processes including job postings, candidate screening, and interview scheduling",
        "parent_agent_name": "triage_agent",
        "agent_type": "sub_agent",
        "default_model": "gpt-4o",
        "is_active": True
    },
    {
        "name": "travel_expense_agent",
        "display_name": "Travel Expense Agent",
        "description": "Manages travel expense claims, reimbursements, and travel request approvals",
        "parent_agent_name": "triage_agent",
        "agent_type": "sub_agent",
        "default_model": "gpt-4o",
        "is_active": True
    }
]

def add_4_agents_safely():
    """Safely add only the 4 new agents without touching anything else"""
    db = next(get_db())
    
    try:
        logger.info("=" * 80)
        logger.info("Starting SAFE addition of 4 new agents")
        logger.info("=" * 80)
        
        # Check if triage_agent exists and get its ID
        triage_result = db.execute(text("""
            SELECT id FROM agents WHERE name = 'triage_agent'
        """))
        triage_row = triage_result.fetchone()
        
        if not triage_row:
            logger.error("❌ ABORT: triage_agent not found in database!")
            logger.error("Cannot set parent relationship. Please ensure triage_agent exists first.")
            return False
        
        triage_id = triage_row[0]
        logger.info(f"✅ Found triage_agent with ID: {triage_id}")
        logger.info("")
        
        # Add each agent
        added_count = 0
        skipped_count = 0
        
        for agent in NEW_AGENTS:
            try:
                # Check if agent already exists
                check_result = db.execute(text("""
                    SELECT id, display_name FROM agents WHERE name = :name
                """), {'name': agent['name']})
                existing = check_result.fetchone()
                
                if existing:
                    logger.warning(f"⏭️  SKIP: {agent['name']} already exists (ID: {existing[0]})")
                    skipped_count += 1
                    continue
                
                # Insert the new agent
                agent_data = {
                    'name': agent['name'],
                    'display_name': agent['display_name'],
                    'description': agent['description'],
                    'parent_agent_id': triage_id,  # Set parent to triage_agent
                    'agent_type': agent['agent_type'],
                    'default_model': agent['default_model'],
                    'is_active': agent['is_active']
                }
                
                db.execute(text("""
                    INSERT INTO agents (name, display_name, description, parent_agent_id, 
                                      agent_type, default_model, is_active, created_at, updated_at)
                    VALUES (:name, :display_name, :description, :parent_agent_id,
                            :agent_type, :default_model, :is_active, NOW(), NOW())
                """), agent_data)
                
                logger.info(f"✅ ADDED: {agent['name']}")
                logger.info(f"   Display: {agent['display_name']}")
                logger.info(f"   Parent: triage_agent (ID: {triage_id})")
                logger.info(f"   Type: {agent['agent_type']}")
                logger.info("")
                added_count += 1
                
            except Exception as e:
                logger.error(f"❌ ERROR adding {agent['name']}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        
        # Summary
        logger.info("=" * 80)
        logger.info("SUMMARY:")
        logger.info(f"  ✅ Added: {added_count} agents")
        logger.info(f"  ⏭️  Skipped: {skipped_count} agents (already exist)")
        logger.info(f"  ❌ Failed: {len(NEW_AGENTS) - added_count - skipped_count} agents")
        logger.info("=" * 80)
        logger.info("")
        
        if added_count > 0:
            logger.info("✅ SUCCESS! Agents added to database.")
            logger.info("")
            logger.info("⚠️  IMPORTANT:")
            logger.info("   These agents are NOT yet mapped to any company.")
            logger.info("   They will NOT be accessible until you:")
            logger.info("   1. Add them to agent_mappings table, OR")
            logger.info("   2. Run the full seed script with these agents in agent_mappings")
            logger.info("")
            logger.info("📝 To verify, run:")
            logger.info("   SELECT id, name, display_name, parent_agent_id FROM agents")
            logger.info("   WHERE name IN ('attendance_agent', 'payroll_agent', 'recruiting_agent', 'travel_expense_agent');")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║          SAFE SCRIPT: Add 4 New Agents Only                             ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print("")
    print("This script will:")
    print("  ✅ Add 4 new agents to 'agents' table")
    print("  ✅ Set parent to 'triage_agent'")
    print("  ✅ Skip if agents already exist")
    print("")
    print("This script will NOT:")
    print("  ❌ Modify existing agents")
    print("  ❌ Delete any data")
    print("  ❌ Touch agent_mappings table")
    print("  ❌ Affect production/deployed code")
    print("")
    print("═" * 76)
    
    try:
        success = add_4_agents_safely()
        if success:
            print("")
            print("✅ Script completed successfully!")
            sys.exit(0)
        else:
            print("")
            print("❌ Script failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        print("")
        print(f"❌ Script failed with error: {e}")
        sys.exit(1)

