from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from datetime import datetime

from database.models import LLMCredentials, Company, AgentMapping, Agent
from services.timezone_utils import to_ist
from services.encryption_service import encrypt_api_key
from services.cache_invalidation_service import cache_invalidation_service
from logger import logger


def get_llm_credential_by_id_data(db: Session, credential_id: int):
    """
    Get a single LLM credential by ID.
    
    Args:
        db: Database session
        credential_id: The ID of the credential to retrieve
    
    Returns:
        JSONResponse with credential data or error
    """
    try:
        credential = db.query(LLMCredentials).filter(
            LLMCredentials.id == credential_id,
            LLMCredentials.company_id.isnot(None)  # Exclude NULL company_id
        ).first()
        
        if not credential:
            return JSONResponse(
                status_code=404, 
                content={"status": "error", "message": "LLM credential not found"}
            )
        
        credential_data = {
            "id": credential.id,
            "company_id": credential.company_id,
            "provider": credential.provider,
            "base_url": credential.base_url,
            "api_key": credential.api_key,
            "available_models": credential.available_models,
            "is_default": credential.is_default,
            "max_tokens": credential.max_tokens,
            "temperature": credential.temperature,
            "tts_service": credential.tts_service,
            "cartesia_api_key": credential.cartesia_api_key,
            "deepgram_api_key": credential.deepgram_api_key,
            "openai_api_key": credential.openai_api_key,
            "is_active": credential.is_active,
            "is_crm_flow_active": credential.is_crm_flow_active,
            "crm_accounts_ids": credential.crm_accounts_ids,
            "tags": credential.tags,
            "created_at": to_ist(credential.created_at) if credential.created_at else None,
            "updated_at": to_ist(credential.updated_at) if credential.updated_at else None
        }
        
        return JSONResponse(
            status_code=200, 
            content={
                "status": "success", 
                "message": "LLM credential retrieved successfully", 
                "data": credential_data
            }
        )
    except Exception as e:
        logger.error(f"Error getting LLM credential {credential_id}: {str(e)}")
        raise


def get_llm_credential_data(
    db: Session,
    company_id: Optional[int] = None,
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Get LLM credentials with optional filters and pagination.
    
    Args:
        db: Database session
        company_id: Filter by company ID
        provider: Filter by provider (partial match, case-insensitive)
        is_active: Filter by active status (True/False/None for all)
        page: Page number (starts from 1)
        page_size: Number of items per page
    
    Returns:
        JSONResponse with paginated LLM credentials data
    """
    try:
        query = db.query(LLMCredentials)
        
        # IMPORTANT: Explicitly exclude credentials with NULL company_id
        # These should never exist due to schema constraints, but this provides extra safety
        query = query.filter(LLMCredentials.company_id.isnot(None))
        
        # Apply filters if provided
        if company_id:
            query = query.filter(LLMCredentials.company_id == company_id)
        
        if provider:
            query = query.filter(LLMCredentials.provider.ilike(f"%{provider}%"))
        
        if is_active is not None:
            query = query.filter(LLMCredentials.is_active == is_active)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        llm_credentials = query.order_by(LLMCredentials.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        credentials_data = [
            {
                "id": cred.id,
                "company_id": cred.company_id,
                "provider": cred.provider,
                "base_url": cred.base_url,
                "api_key": cred.api_key,
                "available_models": cred.available_models,
                "is_default": cred.is_default,
                "max_tokens": cred.max_tokens,
                "temperature": cred.temperature,
                "tts_service": cred.tts_service,
                "cartesia_api_key": cred.cartesia_api_key,
                "deepgram_api_key": cred.deepgram_api_key,
                "openai_api_key": cred.openai_api_key,
                "is_crm_flow_active": cred.is_crm_flow_active,
                "crm_accounts_ids": cred.crm_accounts_ids,
                "tags": cred.tags,
                "is_active": cred.is_active,
                "created_at": to_ist(cred.created_at) if cred.created_at else None,
                "updated_at": to_ist(cred.updated_at) if cred.updated_at else None,
                "created_by": cred.created_by,
                "updated_by": cred.updated_by
            }
            for cred in llm_credentials
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Retrieved {len(credentials_data)} LLM credentials (page {page} of {total_pages})",
                "data": credentials_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_items": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting LLM credential data: {str(e)}")
        raise


def create_llm_credential_data(db: Session, credentials_data: Dict[str, Any], created_by: int = None):
    """
    Create new LLM credentials.
    
    Args:
        db: Database session
        credentials_data: LLM credentials data dictionary
        created_by: User ID who is creating the LLM credentials
    
    Returns:
        JSONResponse with created LLM credentials data
    """
    try:
        # Check if company exists
        company = db.query(Company).filter(Company.id == credentials_data["company_id"]).first()
        if not company:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Company with ID {credentials_data['company_id']} does not exist"
                }
            )
        
        # Make a copy to avoid modifying the original data
        encrypted_data = credentials_data.copy()
        
        # Encrypt API keys before storing
        api_key_fields = ['api_key', 'cartesia_api_key', 'deepgram_api_key', 'openai_api_key']
        for key_field in api_key_fields:
            if key_field in encrypted_data and encrypted_data[key_field]:
                try:
                    encrypted_data[key_field] = encrypt_api_key(encrypted_data[key_field])
                    logger.info(f"{key_field} encrypted before storing")
                except Exception as e:
                    logger.error(f"Failed to encrypt {key_field} during creation: {str(e)}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "message": f"Failed to encrypt {key_field}: {str(e)}"
                        }
                    )
        
        # Create new LLM credentials
        llm_credentials = LLMCredentials(
            company_id=encrypted_data["company_id"],
            provider=encrypted_data["provider"],
            base_url=encrypted_data["base_url"],
            api_key=encrypted_data["api_key"],
            available_models=encrypted_data["available_models"],
            is_default=encrypted_data.get("is_default", False),
            max_tokens=encrypted_data.get("max_tokens"),
            temperature=encrypted_data.get("temperature"),
            tts_service=encrypted_data.get("tts_service"),
            cartesia_api_key=encrypted_data.get("cartesia_api_key"),
            deepgram_api_key=encrypted_data.get("deepgram_api_key"),
            openai_api_key=encrypted_data.get("openai_api_key"),
            is_crm_flow_active=encrypted_data.get("is_crm_flow_active", False),
            crm_accounts_ids=encrypted_data.get("crm_accounts_ids"),
            tags=encrypted_data.get("tags"),
            is_active=encrypted_data.get("is_active", True),
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(llm_credentials)
        db.commit()
        db.refresh(llm_credentials)
        
        # Format response data
        created_credentials = {
            "id": llm_credentials.id,
            "company_id": llm_credentials.company_id,
            "provider": llm_credentials.provider,
            "base_url": llm_credentials.base_url,
            "api_key": llm_credentials.api_key,
            "available_models": llm_credentials.available_models,
            "is_default": llm_credentials.is_default,
            "max_tokens": llm_credentials.max_tokens,
            "temperature": llm_credentials.temperature,
            "tts_service": llm_credentials.tts_service,
            "cartesia_api_key": llm_credentials.cartesia_api_key,
            "deepgram_api_key": llm_credentials.deepgram_api_key,
            "openai_api_key": llm_credentials.openai_api_key,
            "is_crm_flow_active": llm_credentials.is_crm_flow_active,
            "crm_accounts_ids": llm_credentials.crm_accounts_ids,
            "tags": llm_credentials.tags,
            "is_active": llm_credentials.is_active,
            "created_at": to_ist(llm_credentials.created_at) if llm_credentials.created_at else None,
            "updated_at": to_ist(llm_credentials.updated_at) if llm_credentials.updated_at else None,
            "created_by": llm_credentials.created_by,
            "updated_by": llm_credentials.updated_by
        }
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "LLM credentials created successfully",
                "data": created_credentials
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating LLM credential: {str(e)}")
        raise


def update_llm_credential_data(db: Session, credentials_id: int, update_data: Dict[str, Any], updated_by: int = None):
    """
    Update LLM credentials by ID.
    
    Args:
        db: Database session
        credentials_id: LLM credentials ID
        update_data: Data to update
        updated_by: User ID who is updating the LLM credentials
    
    Returns:
        JSONResponse with updated LLM credentials data
    """
    try:
        # Find the LLM credentials
        llm_credentials = db.query(LLMCredentials).filter(LLMCredentials.id == credentials_id).first()
        if not llm_credentials:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "LLM credentials not found"
                }
            )
        
        # Check if company_id is being updated and if it exists
        if "company_id" in update_data:
            company = db.query(Company).filter(Company.id == update_data["company_id"]).first()
            if not company:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Company with ID {update_data['company_id']} does not exist"
                    }
                )
        
        # Update fields
        api_key_fields = ['api_key', 'cartesia_api_key', 'deepgram_api_key', 'openai_api_key']
        for key, value in update_data.items():
            if hasattr(llm_credentials, key):
                # Encrypt API keys only if they're being updated and the value is different
                if key in api_key_fields and value:
                    # Get the current encrypted value from database
                    current_encrypted_key = getattr(llm_credentials, key)
                    
                    # Only encrypt if the new value is different from the current encrypted value
                    if value != current_encrypted_key:
                        try:
                            value = encrypt_api_key(value)
                            logger.info(f"{key} encrypted during update (new key provided)")
                        except Exception as e:
                            logger.error(f"Failed to encrypt {key} during update: {str(e)}")
                            return JSONResponse(
                                status_code=500,
                                content={
                                    "status": "error",
                                    "message": f"Failed to encrypt {key}: {str(e)}"
                                }
                            )
                    else:
                        logger.info(f"{key} unchanged, skipping encryption")
                
                setattr(llm_credentials, key, value)
        
        llm_credentials.updated_at = datetime.utcnow()
        if updated_by is not None:
            llm_credentials.updated_by = updated_by
        db.commit()
        db.refresh(llm_credentials)
        
        # Invalidate cache for all agent mappings using this credential
        cache_invalidation_service.invalidate_llm_credentials_for_agent_mappings(
            db, credentials_id, llm_credentials.company_id
        )
        
        # Format response data
        updated_credentials = {
            "id": llm_credentials.id,
            "company_id": llm_credentials.company_id,
            "provider": llm_credentials.provider,
            "base_url": llm_credentials.base_url,
            "api_key": llm_credentials.api_key,
            "available_models": llm_credentials.available_models,
            "is_default": llm_credentials.is_default,
            "max_tokens": llm_credentials.max_tokens,
            "temperature": llm_credentials.temperature,
            "tts_service": llm_credentials.tts_service,
            "cartesia_api_key": llm_credentials.cartesia_api_key,
            "deepgram_api_key": llm_credentials.deepgram_api_key,
            "openai_api_key": llm_credentials.openai_api_key,
            "is_crm_flow_active": llm_credentials.is_crm_flow_active,
            "crm_accounts_ids": llm_credentials.crm_accounts_ids,
            "tags": llm_credentials.tags,
            "is_active": llm_credentials.is_active,
            "created_at": to_ist(llm_credentials.created_at) if llm_credentials.created_at else None,
            "updated_at": to_ist(llm_credentials.updated_at) if llm_credentials.updated_at else None,
            "created_by": llm_credentials.created_by,
            "updated_by": llm_credentials.updated_by
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "LLM credentials updated successfully",
                "data": updated_credentials
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating LLM credential {credentials_id}: {str(e)}")
        raise


def delete_llm_credential_data(db: Session, credentials_id: int):
    """
    Delete LLM credentials by ID with relationship integrity checks.
    
    Args:
        db: Database session
        credentials_id: LLM credentials ID
    
    Returns:
        JSONResponse with deletion status
    """
    try:
        # Find the LLM credentials
        llm_credentials = db.query(LLMCredentials).filter(LLMCredentials.id == credentials_id).first()
        if not llm_credentials:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "LLM credentials not found"
                }
            )
        
        # Check for dependent records in AgentMapping and fetch details
        agent_mappings = db.query(AgentMapping).filter(
            AgentMapping.llm_credentials_id == credentials_id
        ).all()
        
        if len(agent_mappings) > 0:
            # Gather detailed information about which agents are using this credential
            mapped_agents = []
            for mapping in agent_mappings:
                agent = db.query(Agent).filter(Agent.id == mapping.agent_id).first()
                company = db.query(Company).filter(Company.id == mapping.company_id).first()
                
                if agent and company:
                    mapped_agents.append({
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_display_name": agent.display_name,
                        "company_id": company.id,
                        "company_name": company.name,
                        "mapping_id": mapping.id,
                        "is_active": mapping.is_active
                    })
            
            # Create a user-friendly error message
            agent_details_text = []
            for agent_info in mapped_agents:
                status = "Active" if agent_info["is_active"] else "Inactive"
                agent_details_text.append(
                    f"• {agent_info['agent_display_name']} ({agent_info['agent_name']}) in company '{agent_info['company_name']}' [{status}]"
                )
            
            agents_list_message = "\n".join(agent_details_text)
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Cannot delete LLM credentials. It is currently mapped to {len(agent_mappings)} agent(s). Please remove these agent mappings first:\n\n{agents_list_message}",
                    "mapped_agents": mapped_agents,
                    "total_mappings": len(agent_mappings)
                }
            )
        
        # Safe to delete - no dependencies
        # Store company_id before deletion for cache invalidation
        company_id = llm_credentials.company_id
        
        db.delete(llm_credentials)
        db.commit()
        
        # Invalidate cache (even though no mappings exist, clear any stale cache)
        cache_invalidation_service.invalidate_llm_credentials_for_agent_mappings(
            db, credentials_id, company_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "LLM credentials deleted successfully"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting LLM credential {credentials_id}: {str(e)}")
        raise


def toggle_llm_credential_status_data(db: Session, credentials_id: int, updated_by: int = None):
    """
    Toggle the active status of LLM credentials.
    
    Args:
        db: Database session
        credentials_id: LLM credentials ID
        updated_by: User ID who is toggling the LLM credential status
    
    Returns:
        JSONResponse with updated LLM credentials data
    """
    try:
        # Find the LLM credentials
        llm_credentials = db.query(LLMCredentials).filter(LLMCredentials.id == credentials_id).first()
        if not llm_credentials:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "LLM credentials not found"
                }
            )
        
        # Toggle the status
        llm_credentials.is_active = not llm_credentials.is_active
        llm_credentials.updated_at = datetime.utcnow()
        if updated_by is not None:
            llm_credentials.updated_by = updated_by
        db.commit()
        db.refresh(llm_credentials)
        
        # Invalidate cache for all agent mappings using this credential
        cache_invalidation_service.invalidate_llm_credentials_for_agent_mappings(
            db, credentials_id, llm_credentials.company_id
        )
        
        # Format response data
        updated_credentials = {
            "id": llm_credentials.id,
            "company_id": llm_credentials.company_id,
            "provider": llm_credentials.provider,
            "base_url": llm_credentials.base_url,
            "api_key": llm_credentials.api_key,
            "available_models": llm_credentials.available_models,
            "is_default": llm_credentials.is_default,
            "max_tokens": llm_credentials.max_tokens,
            "temperature": llm_credentials.temperature,
            "tts_service": llm_credentials.tts_service,
            "cartesia_api_key": llm_credentials.cartesia_api_key,
            "deepgram_api_key": llm_credentials.deepgram_api_key,
            "openai_api_key": llm_credentials.openai_api_key,
            "is_crm_flow_active": llm_credentials.is_crm_flow_active,
            "crm_accounts_ids": llm_credentials.crm_accounts_ids,
            "tags": llm_credentials.tags,
            "is_active": llm_credentials.is_active,
            "created_at": to_ist(llm_credentials.created_at) if llm_credentials.created_at else None,
            "updated_at": to_ist(llm_credentials.updated_at) if llm_credentials.updated_at else None,
            "created_by": llm_credentials.created_by,
            "updated_by": llm_credentials.updated_by
        }
        
        status_text = "activated" if llm_credentials.is_active else "deactivated"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"LLM credentials {status_text} successfully",
                "data": updated_credentials
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling LLM credential status {credentials_id}: {str(e)}")
        raise


def toggle_llm_credential_crm_flow_data(db: Session, credentials_id: int, updated_by: int = None):
    """
    Toggle the CRM flow status of LLM credentials.
    
    Args:
        db: Database session
        credentials_id: LLM credentials ID
        updated_by: User ID who is toggling the CRM flow status
    
    Returns:
        JSONResponse with updated LLM credentials data
    """
    try:
        # Find the LLM credentials
        llm_credentials = db.query(LLMCredentials).filter(LLMCredentials.id == credentials_id).first()
        if not llm_credentials:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "LLM credentials not found"
                }
            )
        
        # Toggle the CRM flow status
        llm_credentials.is_crm_flow_active = not llm_credentials.is_crm_flow_active
        llm_credentials.updated_at = datetime.utcnow()
        if updated_by is not None:
            llm_credentials.updated_by = updated_by
        db.commit()
        db.refresh(llm_credentials)
        
        # Invalidate cache for all agent mappings using this credential
        cache_invalidation_service.invalidate_llm_credentials_for_agent_mappings(
            db, credentials_id, llm_credentials.company_id
        )
        
        # Format response data
        updated_credentials = {
            "id": llm_credentials.id,
            "company_id": llm_credentials.company_id,
            "provider": llm_credentials.provider,
            "base_url": llm_credentials.base_url,
            "api_key": llm_credentials.api_key,
            "available_models": llm_credentials.available_models,
            "is_default": llm_credentials.is_default,
            "max_tokens": llm_credentials.max_tokens,
            "temperature": llm_credentials.temperature,
            "tts_service": llm_credentials.tts_service,
            "cartesia_api_key": llm_credentials.cartesia_api_key,
            "deepgram_api_key": llm_credentials.deepgram_api_key,
            "openai_api_key": llm_credentials.openai_api_key,
            "is_crm_flow_active": llm_credentials.is_crm_flow_active,
            "crm_accounts_ids": llm_credentials.crm_accounts_ids,
            "tags": llm_credentials.tags,
            "is_active": llm_credentials.is_active,
            "created_at": to_ist(llm_credentials.created_at) if llm_credentials.created_at else None,
            "updated_at": to_ist(llm_credentials.updated_at) if llm_credentials.updated_at else None,
            "created_by": llm_credentials.created_by,
            "updated_by": llm_credentials.updated_by
        }
        
        status_text = "enabled" if llm_credentials.is_crm_flow_active else "disabled"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"CRM Flow {status_text} successfully",
                "data": updated_credentials
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling LLM credential CRM flow {credentials_id}: {str(e)}")
        raise


def get_llm_credentials_by_company_and_agent_data(db: Session, company_id: int, agent_name: str, origin: str = None):
    """
    Get LLM credentials by company_id and agent_name/app_name (with optional origin).
    
    This function:
    1. Verifies the company exists and is active
    2. Verifies the agent exists by agent_name and is active
    3. Finds the agent mapping for the company and agent
    4. Retrieves the associated LLM credentials and verifies it's active
    5. Returns company details, agent details, and LLM credentials
    
    Args:
        db: Database session
        company_id: Company ID
        agent_name: Agent/Application name (agent_name or app_name - works with both)
        origin: (Optional) Origin URL - kept for backward compatibility, currently not used in logic
    
    Returns:
        JSONResponse with company, agent, and LLM credentials data or error
    """
    try:
        # Import here to avoid circular imports
        from database.models import Agent, AgentMapping
        
        # 1. Check if company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"Company with ID {company_id} not found",
                "data": None
            })
        
        # 2. Check if company is active
        if not company.is_active:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": f"Company '{company.name}' (ID: {company_id}) is inactive. Please activate the company first.",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "company_is_active": company.is_active,
                    "reason": "company_inactive"
                }
            })
        
        # 3. Check if agent exists by name
        agent = db.query(Agent).filter(Agent.name == agent_name).first()
        if not agent:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"Agent with name '{agent_name}' not found",
                "data": None
            })
        
        # 4. Check if agent is active
        if not agent.is_active:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": f"Agent '{agent.display_name}' (name: {agent.name}) is inactive. Please activate the agent first.",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "company_is_active": company.is_active,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_display_name": agent.display_name,
                    "agent_is_active": agent.is_active,
                    "reason": "agent_inactive"
                }
            })
        
        # 5. Find agent mapping for this company and agent
        agent_mapping = db.query(AgentMapping).filter(
            AgentMapping.company_id == company_id,
            AgentMapping.agent_id == agent.id
        ).first()
        
        if not agent_mapping:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"No agent mapping found for company '{company.name}' and agent '{agent.display_name}'",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_display_name": agent.display_name,
                    "reason": "agent_mapping_not_found"
                }
            })
        
        # 6. Check if agent mapping is active
        if not agent_mapping.is_active:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": f"Agent mapping for company '{company.name}' and agent '{agent.display_name}' is inactive. Please activate the agent mapping first.",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "company_is_active": company.is_active,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_display_name": agent.display_name,
                    "agent_is_active": agent.is_active,
                    "agent_mapping_is_active": agent_mapping.is_active,
                    "reason": "agent_mapping_inactive"
                }
            })
        
        # 7. Get LLM credentials
        llm_credentials = db.query(LLMCredentials).filter(
            LLMCredentials.id == agent_mapping.llm_credentials_id
        ).first()
        
        if not llm_credentials:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"LLM credentials with ID {agent_mapping.llm_credentials_id} not found",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_display_name": agent.display_name,
                    "llm_credentials_id": agent_mapping.llm_credentials_id,
                    "reason": "llm_credentials_not_found"
                }
            })
        
        # 8. Check if LLM credentials are active
        if not llm_credentials.is_active:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": f"LLM credentials (provider: {llm_credentials.provider}) are inactive. Please activate the credentials first.",
                "data": {
                    "company_id": company.id,
                    "company_name": company.name,
                    "company_is_active": company.is_active,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_display_name": agent.display_name,
                    "agent_is_active": agent.is_active,
                    "agent_mapping_is_active": agent_mapping.is_active,
                    "llm_credentials_id": llm_credentials.id,
                    "llm_credentials_provider": llm_credentials.provider,
                    "llm_credentials_is_active": llm_credentials.is_active,
                    "reason": "llm_credentials_inactive"
                }
            })
        
        # 9. All checks passed - return success response with LLM credentials only
        llm_credentials_data = {
            "id": llm_credentials.id,
            "company_id": llm_credentials.company_id,
            "provider": llm_credentials.provider,
            "base_url": llm_credentials.base_url,
            "api_key": llm_credentials.api_key,
            "available_models": llm_credentials.available_models,
            "is_default": llm_credentials.is_default,
            "max_tokens": llm_credentials.max_tokens,
            "temperature": llm_credentials.temperature,
            "is_active": llm_credentials.is_active,
            "is_crm_flow_active": llm_credentials.is_crm_flow_active,
            "crm_accounts_ids": llm_credentials.crm_accounts_ids,
            "tts_service": llm_credentials.tts_service,
            "cartesia_api_key": llm_credentials.cartesia_api_key,
            "deepgram_api_key": llm_credentials.deepgram_api_key,
            "openai_api_key": llm_credentials.openai_api_key,
            "tags": llm_credentials.tags,
            "created_at": to_ist(llm_credentials.created_at) if llm_credentials.created_at else None,
            "updated_at": to_ist(llm_credentials.updated_at) if llm_credentials.updated_at else None,
            "created_by": llm_credentials.created_by,
            "updated_by": llm_credentials.updated_by
        }
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": f"Successfully retrieved credentials for company '{company.name}' and agent '{agent.display_name}'",
            "data": llm_credentials_data
        })

    except Exception as e:
        logger.error(f"Error in get_llm_credentials_by_company_and_agent_data: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "data": None
        })
