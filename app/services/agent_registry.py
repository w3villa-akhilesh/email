from typing import List, Optional, Dict, Tuple
from app.models.db_models import Company, Agent, AgentMapping, LLMCredentials
from app.services.my_sql_client import get_db
from app.utils.logger import logger
from sqlalchemy.orm import Session
from app.services.redis_cache_service import cache_service

class AgentRegistryService:
    
    @staticmethod
    def get_company_agents(company_id: int, agent_type: str = None) -> List[Agent]:
        """Get all active agents for a company with caching"""
        # Check cache first
        cached_agents_data = cache_service.get_cached_company_agents(company_id, agent_type)
        if cached_agents_data:
            logger.debug(f"Retrieved {len(cached_agents_data)} agents from cache for company {company_id}")
            # Convert cached data back to Agent-like objects for compatibility
            # Note: These are dict objects, not full SQLAlchemy Agent objects
            return cached_agents_data
        
        # Fetch from database if not in cache
        db = next(get_db())
        try:
            query = db.query(Agent).join(AgentMapping).filter(
                AgentMapping.company_id == company_id,
                AgentMapping.is_active == True,
                Agent.is_active == True
            )
            
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
                
            agents = query.all()
            
            # Cache the results
            cache_service.cache_company_agents(company_id, agent_type, agents)
            logger.debug(f"Cached {len(agents)} agents for company {company_id}")
            
            return agents
        finally:
            db.close()
    
    @staticmethod
    def get_company_agents_by_id(company_id: int, agent_type: str = None) -> List[Agent]:
        """Get all active agents for a company by company ID - ONLY from agent_mappings with caching"""
        # Check cache first
        cached_agents_data = cache_service.get_cached_company_agents(company_id, agent_type)
        if cached_agents_data:
            logger.debug(f"Retrieved {len(cached_agents_data)} agents from cache for company {company_id}")
            return cached_agents_data
        
        # Fetch from database if not in cache
        db = next(get_db())
        try:
            # Always fetch from agent_mappings table - this is the source of truth for company-agent associations
            query = db.query(Agent).join(
                AgentMapping, Agent.id == AgentMapping.agent_id
            ).filter(
                AgentMapping.company_id == company_id,
                AgentMapping.is_active == True,
                Agent.is_active == True
            )
            
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
                
            agents = query.all()
            
            # Cache the results
            cache_service.cache_company_agents(company_id, agent_type, agents)
            logger.debug(f"Cached {len(agents)} agents for company {company_id}")
            
            return agents
        finally:
            db.close()
    
    @staticmethod
    def get_child_agent_names_for_company_by_id(company_id: int, parent_agent_name: str) -> List[str]:
        """Get list of child agent names for a specific parent agent and company with caching"""
        # Check cache first
        cached_child_names = cache_service.get_cached_child_agents(company_id, parent_agent_name)
        if cached_child_names is not None:
            logger.debug(f"Retrieved {len(cached_child_names)} child agents from cache for parent '{parent_agent_name}' in company {company_id}")
            return cached_child_names
        
        # Fetch from database if not in cache
        db = next(get_db())
        try:
            # First get the parent agent ID
            parent_agent = db.query(Agent).filter(
                Agent.name == parent_agent_name,
                Agent.is_active == True
            ).first()
            
            if not parent_agent:
                logger.warning(f"Parent agent '{parent_agent_name}' not found")
                # Cache empty result to avoid repeated DB queries
                cache_service.cache_child_agents(company_id, parent_agent_name, [])
                return []
            
            # Get child agents that are mapped to the company
            child_agents = db.query(Agent).join(
                AgentMapping, Agent.id == AgentMapping.agent_id
            ).filter(
                Agent.parent_agent_id == parent_agent.id,  # Child of the parent agent
                AgentMapping.company_id == company_id,     # Mapped to the company
                AgentMapping.is_active == True,            # Active mapping
                Agent.is_active == True                    # Active agent
            ).all()
            
            child_names = [agent.name for agent in child_agents]
            logger.info(f"Found child agents for '{parent_agent_name}' in company {company_id}: {child_names}")
            
            # Cache the results
            cache_service.cache_child_agents(company_id, parent_agent_name, child_names)
            logger.debug(f"Cached {len(child_names)} child agents for parent '{parent_agent_name}' in company {company_id}")
            
            return child_names
            
        finally:
            db.close()
    
    @staticmethod
    def get_agent_init_function(agent_name: str):
        """Get the initialization function for a specific agent"""
        # Import agent initialization functions dynamically
        try:
            if agent_name == "hrms_agent":
                from app.helpers.hrms_agent import initiate_hrms_agent
                return initiate_hrms_agent
            elif agent_name == "pm_board_story_agent":
                from app.helpers.pm_board_story_agent import initiate_story_agent
                return initiate_story_agent
            elif agent_name == "calling_agent":
                from app.helpers.calling_agent import initiate_calling_agent
                return initiate_calling_agent
            elif agent_name == "pms_agent":
                from app.helpers.pms_agent import initiate_pms_agent
                return initiate_pms_agent
            elif agent_name == "leave_agent":
                from app.helpers.leave_agent.leave_agent import initiate_leave_agent
                return initiate_leave_agent
            elif agent_name == "ats_agent":
                from app.helpers.ats_agent import initiate_ats_agent
                return initiate_ats_agent
            elif agent_name == "resume_parser":
                from app.helpers.resume_parser_agent import initiate_resume_parser_agent
                return initiate_resume_parser_agent
            elif agent_name == "transcribe_agent":
                from app.helpers.transcribe_agent import initiate_transcribe_agent
                return initiate_transcribe_agent
            elif agent_name == "crm_faq_agent":
                from app.helpers.crm_faq_agent import initiate_crm_faq_agent
                return initiate_crm_faq_agent
            elif agent_name == "crm_triage_agent":
                from app.helpers.crm_triage import initiate_crm_triage_agent
                return initiate_crm_triage_agent
            elif agent_name == "iats_agent":
                from app.helpers.iats import initiate_iats_agent
                return initiate_iats_agent
            # elif agent_name == "performance_evaluation_agent":
            #     from app.helpers.performance_evaluation_agent import initiate_performance_evaluation_agent
            #     return initiate_performance_evaluation_agent
            elif agent_name == "lms_agent":
                from app.helpers.lms_agent import initiate_lms_agent
                return initiate_lms_agent
            elif agent_name == "link_generating_agent":
                from app.helpers.link_generating_agent import initiate_link_generating_agent
                return initiate_link_generating_agent
            elif agent_name == "user_agent":
                from app.helpers.user_agent import user_agent
                return user_agent
            # Rexnord agents
            elif agent_name == "rexnord_triage_agent":
                from rexnord.helpers.rexnord_triage_agent import initiate_rexnord_agent
                return initiate_rexnord_agent
            elif agent_name == "dealer_agent":
                from rexnord.helpers.dealer_agent import initiate_dealer_agent
                return initiate_dealer_agent
            elif agent_name == "product_agent":
                from rexnord.helpers.product_agent import initiate_product_agent
                return initiate_product_agent
            elif agent_name == "contact_rexnord_agent":
                from rexnord.helpers.contact_rexnord_agent import initiate_contact_rexnord_agent
                return initiate_contact_rexnord_agent
            elif agent_name == "faq_agent":
                from rexnord.helpers.faq_agent import initiate_faq_agent
                return initiate_faq_agent
            elif agent_name == "product_details_agent":
                from rexnord.helpers.product_details_agent import initiate_product_details_agent
                return initiate_product_details_agent
            # CRM Sub-agents
            elif agent_name == "crm_lead_management_agent":
                from app.helpers.crm_subagents.crm_lead_management_agent import initiate_crm_lead_management_agent
                return initiate_crm_lead_management_agent
            elif agent_name == "crm_email_automation_agent":
                from app.helpers.crm_subagents.crm_email_automation_agent import initiate_crm_email_automation_agent
                return initiate_crm_email_automation_agent
            elif agent_name == "crm_sales_automation_agent":
                from app.helpers.crm_subagents.crm_sales_automation_agent import initiate_crm_sales_automation_agent
                return initiate_crm_sales_automation_agent
            elif agent_name == "crm_pipeline_analytics_agent":
                from app.helpers.crm_subagents.crm_pipeline_analytics_agent import initiate_crm_pipeline_analytics_agent
                return initiate_crm_pipeline_analytics_agent
            elif agent_name == "crm_customer_intelligence_agent":
                from app.helpers.crm_subagents.crm_customer_intelligence_agent import initiate_crm_customer_intelligence_agent
                return initiate_crm_customer_intelligence_agent
            # IATS sub-agents
            elif agent_name == "job_profile_agent":
                from app.sub_agents.iats.job_profile_agent import initiate_job_profile_agent
                return initiate_job_profile_agent
            elif agent_name == "candidate_iats_agent":
                from app.sub_agents.iats.candidate_iats_agent import initiate_candidate_iats_agent
                return initiate_candidate_iats_agent
            elif agent_name == "custom_matching_agent":
                from app.sub_agents.iats.custom_matching_agent import initiate_custom_matching_agent
                return initiate_custom_matching_agent
            elif agent_name == "hiring_agent":
                from app.sub_agents.iats.hiring_agent import initiate_hiring_agent
                return initiate_hiring_agent
            elif agent_name == "job_profile_matching_agent":
                from app.sub_agents.iats.job_profile_matching_agent import initiate_job_profile_matching_agent
                return initiate_job_profile_matching_agent
            elif agent_name == "interview_scheduler_agent":
                from app.sub_agents.iats.interview_scheduler_agent import initiate_interview_scheduler_agent
                return initiate_interview_scheduler_agent
            elif agent_name == "matching_criteria_agent":
                from app.sub_agents.iats.matching_criteria_agent import initiate_matching_criteria_agent
                return initiate_matching_criteria_agent
            elif agent_name == "scoring_criteria_agent":
                from app.sub_agents.iats.scoring_criteria_agent import initiate_scoring_criteria_agent
                return initiate_scoring_criteria_agent
            # User sub-agents
            elif agent_name == "user_leave_agent":
                from app.helpers.leave_agent.leave_agent import initiate_leave_agent
                return initiate_leave_agent
            elif agent_name == "user_pm_board_story_agent":
                from app.helpers.pm_board_story_agent import initiate_story_agent
                return initiate_story_agent
            elif agent_name == "attendance_agent":
                from app.helpers.attendance_agent.attendance_agent import initiate_attendance_agent
                return initiate_attendance_agent
            elif agent_name == "payroll_agent":
                from app.helpers.payroll_agent.payroll_agent import initiate_payroll_agent
                return initiate_payroll_agent
            elif agent_name == "recruiting_agent":
                from app.helpers.recruiting_agent.recruiting_agent import initiate_recruiting_agent
                return initiate_recruiting_agent
            elif agent_name == "travel_expense_agent":
                from app.helpers.travel_expense_agent.travel_agent import initiate_travel_expense_agent
                return initiate_travel_expense_agent
            else:
                logger.warning(f"No initialization function found for agent: {agent_name}")
                return None
                
        except ImportError as e:
            logger.error(f"Failed to import initialization function for agent {agent_name}: {e}")
            return None
    
    @staticmethod
    async def create_agent_instance(agent_name: str, **kwargs):
        """Create an agent instance dynamically"""
        init_function = AgentRegistryService.get_agent_init_function(agent_name)
        
        if not init_function:
            raise Exception(f"No initialization function available for agent: {agent_name}")
        
        try:
            # Filter kwargs to only include parameters that the function accepts
            import inspect
            sig = inspect.signature(init_function)
            filtered_kwargs = {}
            
            for param_name in sig.parameters:
                if param_name in kwargs:
                    filtered_kwargs[param_name] = kwargs[param_name]
            
            logger.debug(f"Calling {agent_name} with parameters: {list(filtered_kwargs.keys())}")
            
            # Call the agent initialization function with filtered parameters
            return await init_function(**filtered_kwargs)
        except Exception as e:
            logger.error(f"Failed to create agent instance for {agent_name}: {e}")
            raise
    
    @staticmethod
    async def safe_run_agents(agent_names: List[str], **kwargs) -> Tuple[List, List]:
        """
        Initialize multiple agents safely with error handling
        Returns: (successful_agents, errors)
        """
        successful_agents = []
        errors = []
        
        for agent_name in agent_names:
            try:
                agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
                if agent_instance:
                    successful_agents.append(agent_instance)
                    logger.info(f"Successfully initialized agent: {agent_name}")
            except Exception as e:
                logger.error(f"Error initializing agent {agent_name}: {str(e)}")
                errors.append({"agent": agent_name, "error": str(e)})
        
        return successful_agents, errors