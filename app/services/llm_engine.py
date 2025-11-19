import os
from typing import Optional, Tuple, List, Dict
from google.adk.models.lite_llm import LiteLlm
from app.models.db_models import Company, Agent, LLMCredentials, AgentMapping
from app.services.email_notifier import send_exception_email
from app.services.my_sql_client import get_db
from app.utils.logger import logger
from app.core.exceptions import LLMKeyNotSetException, LLMConfigurationException, LLMInitializationException
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.services.redis_cache_service import cache_service
load_dotenv()

def decrypt_text(ciphertext: str) -> str:
    FERNET_KEY = os.getenv("LLM_ENCRYPTION_KEY")
    fernet = Fernet(FERNET_KEY)
    return fernet.decrypt(ciphertext.encode()).decode()

def get_llm_credentials_by_agent_and_company_id(agent_name: str, company_id: int, db: Session) -> Tuple[str, str, str]:
    """
    Get LLM credentials using agent_name and company_id through agent_mappings ONLY with caching
    ONLY checks agent_mappings table - this is the single source of truth for company-agent associations
    """
    # Check cache first
    cached_credentials = cache_service.get_cached_llm_credentials(agent_name, company_id)
    if cached_credentials:
        logger.debug(f"Retrieved LLM credentials from cache for agent '{agent_name}' and company {company_id}")
        return cached_credentials
    
    # ONLY query through agent_mappings - no direct agent or credential access allowed
    result = db.query(
        AgentMapping,
        Agent,
        LLMCredentials,
        Company
    ).join(
        Agent, AgentMapping.agent_id == Agent.id
    ).join(
        LLMCredentials, AgentMapping.llm_credentials_id == LLMCredentials.id
    ).join(
        Company, AgentMapping.company_id == Company.id  # Fixed: Join on Company.id (primary key)
    ).filter(
        Company.id == company_id,               # Filter by company id
        Agent.name == agent_name,               # Filter by agent name
        AgentMapping.is_active == True,         # MUST have active mapping
        Agent.is_active == True,
        LLMCredentials.is_active == True,
        Company.is_active == True
    ).first()
    
    if not result:
        raise LLMKeyNotSetException(
            app_name=agent_name,
            company_id=str(company_id),
            origin=f"company_id_{company_id}"
        )
    
    mapping, agent, credentials, company = result
    
    # Decrypt the API key
    decrypted_key = decrypt_text(credentials.api_key)
    
    # Use selected_model first, then first available model
    if mapping.selected_model:
        model = mapping.selected_model
    elif credentials.available_models and len(credentials.available_models) > 0:
        model = credentials.available_models[0]
    else:
        # No model available - raise descriptive error
        raise LLMConfigurationException(
            f"No LLM model configured for agent '{agent_name}' in company {company_id}. "
            f"Please configure 'selected_model' in agent_mappings or add models to 'available_models' in llm_credentials table."
        )
    
    # Cache the decrypted credentials
    cache_service.cache_llm_credentials(agent_name, company_id, model, decrypted_key, credentials.base_url)
    logger.debug(f"Cached LLM credentials for agent '{agent_name}' and company {company_id}")
    
    return model, decrypted_key, credentials.base_url

def get_llm_credentials_based_on_company_id(app_name: str, company_id: str, origin: str):
    """
    Get LLM credentials using new association-based system only
    """
    db = next(get_db())
    try:
        # Get company by ID to ensure it exists and is active
        company = db.query(Company).filter(
            Company.id == int(company_id),
            Company.is_active == True
        ).first()

        if not company:
            logger.error(f"Company ID {company_id} not found in database")
            raise LLMKeyNotSetException(
                app_name=app_name,
                company_id=company_id,
                origin=origin
            )
        
        # Use association-based lookup
        logger.info(f"Using association-based system for agent '{app_name}' and company '{company.name}'")
        return get_llm_credentials_by_agent_and_company_id(app_name, int(company_id), db)
        
    finally:
        db.close()

def _get_fallback_llm_engine(agent_name: str) -> LiteLlm:
    """Fallback to environment-based configuration - only for development when no company_id"""
    logger.info(f"Using fallback environment configuration for agent '{agent_name}'")
    
    # Default environment variables
    custom_model = os.getenv("KIVO_AGENT_MODEL", "gpt-4o")  # Default model
    llm_key = os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    
    if not custom_model:
        raise LLMConfigurationException(f"No model configured for {agent_name} and no default model found")

    if not llm_key:
        raise LLMConfigurationException("Missing API key: llm_key not provided")

    if not llm_base_url:
        raise LLMConfigurationException("Missing API base URL: llm_base_url not provided")

    return LiteLlm(
        model=custom_model,
        api_base=llm_base_url,
        api_key=llm_key,
    )


def get_llm_engine(
    agent_name: str,
    company_id: int = None, 
    company_name: str = None,
    app_name: str = None,
    origin: str = None,
    type: str = None
) -> LiteLlm:
    """
    Enhanced LLM engine factory with database-driven configuration

    Args:
        agent_name: Name of the agent requesting LLM access
        company_id: Company ID for credential lookup
        company_name: Company name for credential lookup
        app_name: Application name (legacy compatibility)
        origin: Origin URL for company lookup
    """
    db = next(get_db())
    
    try:
        production_mode = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
        
        if production_mode:
            logger.info(f"PRODUCTION_MODE: {production_mode}, agent_name: {agent_name}, company_id: {company_id}, company_name: {company_name}, origin: {origin}")
            if not (company_id or company_name or origin):
                logger.info(f"PRODUCTION_MODE: no company info provided, using fallback credentials")
                custom_model = os.getenv("KIVO_AGENT_MODEL")
                llm_key = os.getenv("LLM_API_KEY_IF_NOT_COMPANY")
                llm_base_url = os.getenv("LLM_API_BASE_IF_NOT_COMPANY")

                return LiteLlm(
                    model=custom_model,
                    api_base=llm_base_url,
                    api_key=llm_key,
                )

            if company_id:
                logger.info(f"Found company: ID={company_id}, name='{company_name}'")
                # Use new database-driven approach
                model, api_key, base_url = get_llm_credentials_by_agent_and_company_id(agent_name, company_id, db)

                logger.info(f"------> model: {model}, api_key: {api_key}, base_url: {base_url} ---------------->>>")

                logger.info(f"Using database-driven LLM engine for agent '{agent_name}' and company '{company_name}'")
                # litellm is not required for vision and transcription agents, so we return the model, api_key, base_url directly
                if type == 'vision' and type == 'transcribe': 
                    return model, api_key, base_url
                else:
                    return LiteLlm(
                        model=model,
                        api_base=base_url,
                        api_key=api_key,
                    )
            else:
                logger.warning(f"Company not found - company_id: {company_id}, company_name: {company_name}, origin: {origin}, falling back to environment configuration")
        
        # Fallback to environment-based configuration
        return _get_fallback_llm_engine(agent_name)

    except LLMKeyNotSetException:
        # Re-raise LLMKeyNotSetException without modification to preserve its context
        raise
    except Exception as e:
        raise LLMInitializationException(f"An error occurred while initializing LLM engine: {str(e)}", e)
    finally:
        db.close()