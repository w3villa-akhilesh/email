#!/usr/bin/env python3
"""
Agent System Seed Data

This file contains all agent-related seed data in a configurable format.
It populates the database with companies, agents, LLM credentials, and agent mappings.

Usage:
    python agent_seed_data.py
    python agent_seed_data.py --config custom_config.json
    python agent_seed_data.py --clear  # Clear all data first
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.services.my_sql_client import get_db
from app.utils.logger import logger
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# Default configuration
DEFAULT_CONFIG = {
    "companies": [
        {
            "id": 1,  # Explicitly set ID since autoincrement=False
            "name": "demo_kivo_ai",
            "origin": "https://demo.kivo.ai/",
            "is_active": True
        }
    ],
    "agents": [
        # Primary agents (parents)
        {
            "name": "triage_agent",
            "display_name": "Triage Agent",
            "description": "Main coordinator agent that routes queries to appropriate sub-agents",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "iats_agent",
            "display_name": "IATS Agent",
            "description": "Intelligent Applicant Tracking System agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "hrms_agent",
            "display_name": "HRMS Agent",
            "description": "Human Resource Management System agent",
            "parent_agent_name": "triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "user_agent",
            "display_name": "User Agent",
            "description": "Main user-facing agent for direct user interactions",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_triage_agent",
            "display_name": "CRM Triage Agent",
            "description": "CRM coordinator agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        
        # Triage sub-agents
        {
            "name": "calling_agent",
            "display_name": "Calling Agent",
            "description": "Handles call-related requests",
            "parent_agent_name": "triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "pm_board_story_agent",
            "display_name": "PM Board Story Agent",
            "description": "Handles project management board stories",
            "parent_agent_name": "triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "pms_agent",
            "display_name": "PMS Agent",
            "description": "Project Management System agent",
            "parent_agent_name": "triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
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
        },
        
        # HRMS sub-agents
        {
            "name": "leave_agent",
            "display_name": "Leave Agent",
            "description": "Handles leave management requests",
            "parent_agent_name": "hrms_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },

        
        # IATS sub-agents
        {
            "name": "job_profile_agent",
            "display_name": "Job Profile Agent",
            "description": "Handles job profile creation and management",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "candidate_iats_agent",
            "display_name": "Candidate IATS Agent",
            "description": "Handles candidate management in IATS",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "custom_matching_agent",
            "display_name": "Custom Matching Agent",
            "description": "Handles custom job-candidate matching",
            "parent_agent_name": "iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "interview_scheduler_agent",
            "display_name": "Interview Scheduler Agent",
            "description": "Manages interview scheduling, calendar management, and interview coordination",
            "parent_agent_name": "candidate_iats_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },

        
        # User sub-agents
        {
            "name": "user_leave_agent",
            "display_name": "User Leave Agent",
            "description": "Leave management for direct user access",
            "parent_agent_name": "user_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "user_pm_board_story_agent",
            "display_name": "User PM Board Story Agent",
            "description": "Story creation for direct user access",
            "parent_agent_name": "user_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        
        # CRM sub-agents
        {
            "name": "crm_lead_management_agent",
            "display_name": "CRM Lead Management Agent",
            "description": "Handles CRM lead management",
            "parent_agent_name": "crm_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_email_automation_agent",
            "display_name": "CRM Email Automation Agent",
            "description": "Handles CRM email automation",
            "parent_agent_name": "crm_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_sales_automation_agent",
            "display_name": "CRM Sales Automation Agent",
            "description": "Handles CRM sales automation",
            "parent_agent_name": "crm_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_pipeline_analytics_agent",
            "display_name": "CRM Pipeline Analytics Agent",
            "description": "Handles CRM pipeline analytics",
            "parent_agent_name": "crm_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_customer_intelligence_agent",
            "display_name": "CRM Customer Intelligence Agent",
            "description": "Handles CRM customer intelligence",
            "parent_agent_name": "crm_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        
        # Standalone agents
        {
            "name": "ats_agent",
            "display_name": "ATS Agent",
            "description": "Applicant Tracking System agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "transcribe_agent",
            "display_name": "Transcribe Agent",
            "description": "Audio transcription agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "transcription_agent",
            "display_name": "Transcription Agent",
            "description": "Audio transcription and voice note processing agent using OpenAI Whisper",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "whisper-1",
            "is_active": True
        },
        {
            "name": "vision_agent",
            "display_name": "Vision Agent",
            "description": "Image processing and analysis agent for visual content extraction",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "resume_parser",
            "display_name": "Resume Parser",
            "description": "Resume parsing agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "crm_faq_agent",
            "display_name": "CRM FAQ Agent",
            "description": "CRM FAQ handling agent",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },


        
        # Rexnord agents
        {
            "name": "rexnord_triage_agent",
            "display_name": "Rexnord Triage Agent",
            "description": "Main Rexnord coordinator agent that routes queries to dealer, product, contact, and FAQ sub-agents",
            "parent_agent_id": None,
            "agent_type": "primary",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "dealer_agent",
            "display_name": "Dealer Agent",
            "description": "Handles dealer-related queries in Rexnord context",
            "parent_agent_name": "rexnord_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "product_agent",
            "display_name": "Product Agent",
            "description": "Handles product discovery, variants, and catalog navigation in Rexnord context",
            "parent_agent_name": "rexnord_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "contact_rexnord_agent",
            "display_name": "Contact Rexnord Agent",
            "description": "Handles contact and inquiry requests in Rexnord context",
            "parent_agent_name": "rexnord_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "faq_agent",
            "display_name": "FAQ Agent",
            "description": "Handles frequently asked questions in Rexnord context",
            "parent_agent_name": "rexnord_triage_agent",
            "agent_type": "sub_agent",
            "default_model": "gpt-4o",
            "is_active": True
        },
        {
            "name": "product_details_agent",
            "display_name": "Product Details Agent",
            "description": "Provides detailed product information and specifications in Rexnord context",
            "parent_agent_name": "product_agent",
            "agent_type": "tool",
            "default_model": "gpt-4o",
            "is_active": True
        }
    ],
    "llm_credentials": [
        {
            "company_name": "demo_kivo_ai",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "gAAAAABoghEFUz-mZir5RQEtb5RbITytZa5wtv44kViwJeSd0FmrD25vg6sod-pbzDDygFQbI75d_BOSUNMHuLAiQ5brlevE7pv9ou8E4FUR1Oy87yArkHg=",  # This should be encrypted
            "available_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            "is_default": True,
            "max_tokens": None,
            "temperature": "0.7",
            "is_active": True
        }
    ],
    "agent_mappings": [
        # All agents mapped to demo company with default credentials
        {
            "company_name": "demo_kivo_ai",
            "agent_names": [
                "triage_agent", "hrms_agent", "calling_agent", "pm_board_story_agent", "pms_agent",
                "leave_agent", "performance_evaluation_agent", "hrms_questionnaire_workflow_agent",
                "name_suggestion_agent", "iats_agent", "job_profile_agent",
                "candidate_iats_agent", "custom_matching_agent", "hiring_agent", 
                "job_profile_matching_agent", "interview_scheduler_agent", "matching_criteria_agent",
                "scoring_criteria_agent", "user_agent", "user_leave_agent",
                "user_story_agent", "crm_triage_agent", "crm_lead_management_agent", 
                "crm_email_automation_agent", "crm_sales_automation_agent", 
                "crm_pipeline_analytics_agent", "crm_customer_intelligence_agent",
                "ats_agent", "transcribe_agent", "transcription_agent", "vision_agent",
                "resume_parser", "crm_faq_agent", "link_generating_agent", "lms_agent",
                "rexnord_triage_agent", "dealer_agent", "product_agent", 
                "contact_rexnord_agent", "faq_agent", "product_details_agent"
            ],
            "selected_model": "gpt-4o",
            "is_active": True
        }
    ]
}

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key using Fernet encryption"""
    fernet_key = os.getenv("LLM_ENCRYPTION_KEY")
    if not fernet_key:
        logger.warning("LLM_ENCRYPTION_KEY not found, using plain text API key")
        return api_key
    
    fernet = Fernet(fernet_key.encode())
    return fernet.encrypt(api_key.encode()).decode()

def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from file or use default"""
    if config_path and Path(config_path).exists():
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        logger.info("Using default configuration")
        return DEFAULT_CONFIG

def clear_existing_data(db):
    """Clear existing agent-related data"""
    logger.info("Clearing existing agent data...")
    
    clear_statements = [
        "DELETE FROM agent_mappings",
        "DELETE FROM agents",
        "DELETE FROM llm_credentials",  # Delete ALL credentials (including NULL company_id)
        "DELETE FROM companies"
    ]
    
    for statement in clear_statements:
        try:
            db.execute(text(statement))
            logger.info(f"Executed: {statement}")
        except Exception as e:
            logger.warning(f"Failed to execute {statement}: {e}")

def seed_companies(db, companies: List[Dict]):
    """Seed companies data with explicit ID"""
    logger.info("Seeding companies...")
    
    for company in companies:
        try:
            # Since autoincrement=False, we must provide explicit ID
            db.execute(text("""
                INSERT INTO companies (id, name, origin, is_active, created_at, updated_at)
                VALUES (:id, :name, :origin, :is_active, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                is_active = VALUES(is_active),
                updated_at = NOW()
            """), company)
            logger.info(f"Seeded company: {company['name']} (ID: {company['id']})")
        except Exception as e:
            logger.error(f"Failed to seed company {company['name']}: {e}")

def seed_agents(db, agents: List[Dict]):
    """Seed agents data with parent-child relationships"""
    logger.info("Seeding agents...")
    
    # First pass: Create all agents without parent relationships
    for agent in agents:
        try:
            agent_data = agent.copy()
            # Remove parent_agent_name for now, we'll handle it in second pass
            agent_data.pop('parent_agent_name', None)
            if 'parent_agent_name' in agent:
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
            logger.info(f"Seeded agent: {agent['name']}")
        except Exception as e:
            logger.error(f"Failed to seed agent {agent['name']}: {e}")
    
    # Second pass: Update parent relationships (MySQL compatible)
    for agent in agents:
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

def seed_llm_credentials(db, credentials: List[Dict]):
    """Seed LLM credentials data"""
    logger.info("Seeding LLM credentials...")
    
    for cred in credentials:
        try:
            # Get company ID
            company_result = db.execute(text("""
                SELECT id FROM companies WHERE name = :company_name
            """), {'company_name': cred['company_name']})
            company_row = company_result.fetchone()
            
            if not company_row:
                logger.error(f"Company {cred['company_name']} not found")
                continue
            
            company_id = company_row[0]
            
            # Encrypt API key if needed
            api_key = cred['api_key']
            if api_key != "your-encrypted-api-key-here":
                api_key = encrypt_api_key(api_key)
            
            cred_data = {
                'company_id': company_id,
                'provider': cred['provider'],
                'base_url': cred['base_url'],
                'api_key': api_key,
                'available_models': json.dumps(cred['available_models']),
                'is_default': cred['is_default'],
                'max_tokens': cred['max_tokens'],
                'temperature': cred['temperature'],
                'is_active': cred['is_active']
            }
            
            db.execute(text("""
                INSERT INTO llm_credentials (company_id, provider, base_url, api_key, 
                                           available_models, is_default, max_tokens, 
                                           temperature, is_active, created_at, updated_at)
                VALUES (:company_id, :provider, :base_url, :api_key, :available_models,
                        :is_default, :max_tokens, :temperature, :is_active, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                provider = VALUES(provider),
                base_url = VALUES(base_url),
                api_key = VALUES(api_key),
                available_models = VALUES(available_models),
                is_default = VALUES(is_default),
                max_tokens = VALUES(max_tokens),
                temperature = VALUES(temperature),
                is_active = VALUES(is_active),
                updated_at = NOW()
            """), cred_data)
            logger.info(f"Seeded LLM credentials for company: {cred['company_name']}")
        except Exception as e:
            logger.error(f"Failed to seed LLM credentials for {cred['company_name']}: {e}")

def seed_agent_mappings(db, mappings: List[Dict]):
    """Seed agent mappings data"""
    logger.info("Seeding agent mappings...")
    
    for mapping in mappings:
        try:
            # Get company ID
            company_result = db.execute(text("""
                SELECT id FROM companies WHERE name = :company_name
            """), {'company_name': mapping['company_name']})
            company_row = company_result.fetchone()
            
            if not company_row:
                logger.error(f"Company {mapping['company_name']} not found")
                continue
            
            company_id = company_row[0]
            
            # Get default LLM credentials for this company
            cred_result = db.execute(text("""
                SELECT id FROM llm_credentials 
                WHERE company_id = :company_id AND is_default = TRUE
            """), {'company_id': company_id})
            cred_row = cred_result.fetchone()
            
            if not cred_row:
                logger.error(f"No default LLM credentials found for company {mapping['company_name']}")
                continue
            
            llm_credentials_id = cred_row[0]
            
            # Create mappings for each agent
            for agent_name in mapping['agent_names']:
                try:
                    # Get agent ID
                    agent_result = db.execute(text("""
                        SELECT id FROM agents WHERE name = :agent_name
                    """), {'agent_name': agent_name})
                    agent_row = agent_result.fetchone()
                    
                    if not agent_row:
                        logger.warning(f"Agent {agent_name} not found, skipping mapping")
                        continue
                    
                    agent_id = agent_row[0]
                    
                    mapping_data = {
                        'company_id': company_id,
                        'agent_id': agent_id,
                        'llm_credentials_id': llm_credentials_id,
                        'selected_model': mapping['selected_model'],
                        'is_active': mapping['is_active']
                    }
                    
                    db.execute(text("""
                        INSERT INTO agent_mappings (company_id, agent_id, llm_credentials_id,
                                                   selected_model, is_active, created_at, updated_at)
                        VALUES (:company_id, :agent_id, :llm_credentials_id, :selected_model,
                                :is_active, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                        llm_credentials_id = VALUES(llm_credentials_id),
                        selected_model = VALUES(selected_model),
                        is_active = VALUES(is_active),
                        updated_at = NOW()
                    """), mapping_data)
                    logger.info(f"Seeded mapping: {mapping['company_name']} -> {agent_name}")
                except Exception as e:
                    logger.error(f"Failed to seed mapping for {agent_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to seed mappings for company {mapping['company_name']}: {e}")

def run_seed(config_path: str = None, clear_data: bool = False):
    """Run the seed process"""
    db = next(get_db())
    
    try:
        logger.info("Starting agent system seed...")
        
        # Load configuration
        config = load_config(config_path)
        
        # Clear existing data if requested
        if clear_data:
            clear_existing_data(db)
        
        # Seed data in order
        seed_companies(db, config['companies'])
        seed_agents(db, config['agents'])
        seed_llm_credentials(db, config['llm_credentials'])
        seed_agent_mappings(db, config['agent_mappings'])
        
        # Commit all changes
        db.commit()
        logger.info("Seed completed successfully!")
        
        # Show summary
        for table in ['companies', 'agents', 'llm_credentials', 'agent_mappings']:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                logger.info(f"{table}: {count} records")
            except Exception as e:
                logger.warning(f"Could not count {table}: {e}")
                
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed agent system data")
    parser.add_argument("--config", help="Path to custom configuration file")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    
    args = parser.parse_args()
    
    try:
        run_seed(args.config, args.clear)
    except Exception as e:
        logger.error(f"Seed script failed: {e}")
        sys.exit(1)
