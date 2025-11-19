from typing import Dict, Any, Optional
from datetime import datetime
import json
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data
from app.services.elastic_search.connection import get_es_client

async def fetch_platform_details_from_elasticsearch(company_id: str) -> Dict[str, Any]:
    """
    Fetch platform details from Elasticsearch using the specified query.
    
    Returns:
        dict: Platform details from Elasticsearch
    """
    try:
        logger.info("Fetching platform details from Elasticsearch...")
        
        # Get Elasticsearch client
        es_client = get_es_client()
        
        # Elasticsearch query for platforms
        query = {
            "query": {
                "term": {
                    "tag_type.keyword": "Platform"
                }
            }
        }
        
        index_name=f"tags_{company_id}"
        ES_MAX_RESULTS = 100
        response = es_client.search(
            index=index_name,  
            body=query,
            size=ES_MAX_RESULTS
        )
        
        # Extract hits from response
        hits = response.get('hits', {}).get('hits', [])
        platforms = []
        
        for hit in hits:
            source = hit.get('_source', {})
            platform = {
                "id": source.get("id"),
                "name": source.get("name")
            }
            platforms.append(platform)
        
        logger.info(f"Successfully fetched {len(platforms)} platforms from Elasticsearch")
        
        return {
            "success": True,
            "platforms": platforms,
            "total_count": len(platforms)
        }
        
    except Exception as e:
        logger.error(f"Error fetching platform details from Elasticsearch: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "platforms": []
        }


async def fetch_interview_detail_from_elasticsearch(company_id: str, session_id: str, job_profile_id: str) -> Dict[str, Any]:
    """
    Fetch interview details from Elasticsearch using the specified query.
    """
    logger.info(f"Fetching interview details from Elasticsearch for company: {company_id}, session: {session_id}, job profile: {job_profile_id}")
    index_name=f"job_profiles_{company_id}"
    try:
        es_client = get_es_client()
        query = {
            "query": {
                "term": {
                    "id": job_profile_id
                }
            }
        }
        ES_MAX_RESULTS = 100
        response = es_client.search(
            index=index_name,
            body=query,
            size=ES_MAX_RESULTS
        )
        hits = response.get('hits', {}).get('hits', [])
        interviews = []
        interview_rounds = []
        
        if hits:
            source = hits[0].get("_source", {})
            interview_details = source.get("interview_processes", [])
            interview_rounds = source.get("interview_rounds", [])
            
            for hit in interview_details:
                round_type = hit.get("round_type")
                if round_type:
                    interviews.append(round_type)
        response = {
            "success": True,
            "interview_details": interviews,
            "interview_rounds": interview_rounds
        }
        return response
    except Exception as e:
        logger.error(f"Error fetching platform details from Elasticsearch: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "platforms": []
        }
                
async def load_interview_context(app_name: str, callback_context) -> Optional[Any]:
    """
    Load interview context data into the agent state.
    This ensures interview platforms, job profiles, and interviewers are available.
    """
    
    def set_fallback_context(session_id: str = None, app_name: str = None):
        """Helper function to set fallback template variables"""
        try:
            if not session_id:
                session_id = callback_context._invocation_context.session.id
            callback_context.state["session_id"] = session_id
            callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            callback_context.state["interview_platforms"] = []
            callback_context.state["job_profile"] = []
            callback_context.state["interview_rounds"] = []
            logger.debug(f"Setting up fallback context for session: {session_id}")
        except:
            pass  # In case callback_context is not available
    
    try:
        session_id = callback_context._invocation_context.session.id
        logger.info(f"Loading interview context for session: {session_id}")
        
        # Get session data
        session_data = get_session_data(session_id, app_name)
       
        if not session_data:
            logger.warning(f"Session data not found for session: {session_id}")
            set_fallback_context(session_id, app_name)
            return None
        company_id=session_data.get("company_id")
        # Initialize data variables
        platforms = []
        job_profiles = []
        interview_rounds = []
        
        # Get job profile data
        job_profile = session_data.get("job_profile_data")
        job_profile_id = None
        
        if job_profile:
            try:
                job_profile_data = json.loads(job_profile)
                job_profiles = [job_profile_data.get("job_profile")] if job_profile_data.get("job_profile") else []
                job_profile_id = job_profile_data.get("id")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse job profile data: {e}")
                # Fallback: keep job_profiles as empty list
        
        # Fetch platforms from Elasticsearch
        logger.info("Fetching platforms from Elasticsearch...")
        elasticsearch_result = await fetch_platform_details_from_elasticsearch(company_id)
        if elasticsearch_result.get("success"):
            platforms = elasticsearch_result.get("platforms", [])
            temp_platforms = []
            for platform in platforms:
                temp_platforms.append(platform.get("name"))
            platforms = temp_platforms
            logger.info(f"Fetched {len(platforms)} platforms from Elasticsearch")
        else:
            logger.warning("Failed to fetch platforms from Elasticsearch")
            platforms = []
        
        # Fetch interview details and rounds from Elasticsearch
        if company_id and job_profile_id:
            interview_result = await fetch_interview_detail_from_elasticsearch(company_id, session_id, job_profile_id)
            
            if interview_result.get("success"):
                interview_rounds = interview_result.get("interview_details", [])
                logger.info(f"Found {len(interview_rounds)} interview rounds")

        logger.info(f"Interview rounds: {interview_rounds}")
        logger.info(f"interview platforms details: {platforms}")
        # Store data in context
        callback_context.state["session_id"] = session_id
        callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        callback_context.state["interview_platforms"] = platforms
        callback_context.state["job_profile"] = job_profiles
        callback_context.state["interview_rounds"] = interview_rounds
        logger.info(f"Interview context loaded successfully for session: {session_id}")
        logger.info(f"Platforms: {len(platforms)}, Job Profiles: {len(job_profiles)}, Interview Rounds: {len(interview_rounds)}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading interview context: {e}", exc_info=True)
        set_fallback_context()
        return None
