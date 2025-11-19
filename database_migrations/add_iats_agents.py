#!/usr/bin/env python3
"""
Add IATS Agents to Database

This script adds the missing IATS agents to the database with proper parent-child relationships.
Run this after the main agent_seed_data.py has been executed.

Usage:
    python add_iats_agents.py
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

def add_iats_agents():
    """Add missing IATS agents to the database"""
    logger.info("Adding IATS agents to database...")
    
    # IATS agents to add (these should already be in agent_seed_data.py now)
    iats_agents = [
        {
            "name": "hiring_agent",
            "display_name": "Hiring Agent",
            "description": "Handles hiring workflow queries, candidate stage updates, interview scheduling, and offers",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "job_profile_matching_agent",
            "display_name": "Job Profile Matching Agent",
            "description": "Handles matching workflows using criteria from selected job profiles",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "interview_scheduler_agent",
            "display_name": "Interview Scheduler Agent",
            "description": "Manages interview scheduling, calendar management, and interview coordination",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "matching_criteria_agent",
            "display_name": "Matching Criteria Agent",
            "description": "Extracts and processes matching criteria from job profiles",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "scoring_criteria_agent",
            "display_name": "Scoring Criteria Agent",
            "description": "Defines and manages scoring criteria for candidate evaluation",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        }
    ]
    
    db = next(get_db())
    
    try:
        # First pass: Create all agents without parent relationships
        for agent in iats_agents:
            try:
                agent_data = agent.copy()
                # Remove parent_agent_name for now, we'll handle it in second pass
                agent_data.pop('parent_agent_name', None)
                agent_data['parent_agent_id'] = None
                
                db.execute(text("""
                    INSERT INTO agents (name, display_name, description, parent_agent_id, 
                                      agent_type, default_model, is_active, created_at, updated_at)
                    VALUES (:name, :display_name, :description, :parent_agent_id,
                            :agent_type, :default_model, :is_active, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    description = VALUES(description),
                    agent_type = VALUES(agent_type),
                    default_model = VALUES(default_model),
                    is_active = VALUES(is_active),
                    updated_at = NOW()
                """), agent_data)
                logger.info(f"Added/Updated agent: {agent['name']}")
            except Exception as e:
                logger.error(f"Failed to add agent {agent['name']}: {e}")
        
        # Second pass: Update parent relationships
        for agent in iats_agents:
            if 'parent_agent_name' in agent:
                try:
                    # First get the parent ID
                    parent_result = db.execute(text("""
                        SELECT id FROM agents WHERE name = :parent_name
                    """), {'parent_name': agent['parent_agent_name']})
                    parent_row = parent_result.fetchone()
                    
                    if parent_row:
                        parent_id = parent_row[0]
                        # Then update the child agent
                        db.execute(text("""
                            UPDATE agents SET parent_agent_id = :parent_id WHERE name = :agent_name
                        """), {
                            'parent_id': parent_id,
                            'agent_name': agent['name']
                        })
                        logger.info(f"Updated parent relationship: {agent['name']} -> {agent['parent_agent_name']} (ID: {parent_id})")
                    else:
                        logger.error(f"Parent agent '{agent['parent_agent_name']}' not found for {agent['name']}")
                except Exception as e:
                    logger.error(f"Failed to update parent relationship for {agent['name']}: {e}")
        
        # Add agent mappings for demo company
        logger.info("Adding agent mappings for demo company...")
        
        # Get company ID
        company_result = db.execute(text("""
            SELECT id FROM companies WHERE name = 'demo_kivo_ai'
        """))
        company_row = company_result.fetchone()
        
        if not company_row:
            logger.error("Demo company not found!")
            return
        
        company_id = company_row[0]
        
        # Get default LLM credentials
        llm_result = db.execute(text("""
            SELECT id FROM llm_credentials WHERE company_id = :company_id AND is_default = TRUE
        """), {'company_id': company_id})
        llm_row = llm_result.fetchone()
        
        if not llm_row:
            logger.error("Default LLM credentials not found!")
            return
        
        llm_credentials_id = llm_row[0]
        
        # Add mappings for each IATS agent
        for agent in iats_agents:
            try:
                # Get agent ID
                agent_result = db.execute(text("""
                    SELECT id FROM agents WHERE name = :agent_name
                """), {'agent_name': agent['name']})
                agent_row = agent_result.fetchone()
                
                if agent_row:
                    agent_id = agent_row[0]
                    
                    # Insert agent mapping
                    db.execute(text("""
                        INSERT INTO agent_mappings (company_id, agent_id, llm_credentials_id, 
                                                   selected_model, is_active, priority, created_at, updated_at)
                        VALUES (:company_id, :agent_id, :llm_credentials_id, 
                                'gpt-4o', TRUE, 1, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                        selected_model = VALUES(selected_model),
                        is_active = VALUES(is_active),
                        updated_at = NOW()
                    """), {
                        'company_id': company_id,
                        'agent_id': agent_id,
                        'llm_credentials_id': llm_credentials_id
                    })
                    logger.info(f"Added agent mapping: {agent['name']} -> demo_kivo_ai")
                else:
                    logger.error(f"Agent {agent['name']} not found for mapping")
            except Exception as e:
                logger.error(f"Failed to add mapping for {agent['name']}: {e}")
        
        # Commit all changes
        db.commit()
        logger.info("Successfully added all IATS agents and mappings!")
        
    except Exception as e:
        logger.error(f"Error adding IATS agents: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_iats_agents()
