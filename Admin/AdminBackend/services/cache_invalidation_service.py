"""
Cache Invalidation Service for Admin Backend

This service handles Redis cache invalidation when data is modified in the Admin Panel.
It ensures that cached data in the main application stays in sync with database changes.

Note: This service uses the same Redis instance as the main application 
(same REDIS_HOST, REDIS_PORT, REDIS_DB) but maintains its own Redis client.
"""

import os
import redis
import hashlib
from sqlalchemy.orm import Session
from typing import List, Optional
from dotenv import load_dotenv
from logger import logger
from database.models import AgentMapping, Agent

# Load environment variables
load_dotenv()


class CacheInvalidationService:
    """
    Service to handle cache invalidation when Admin Panel modifies data.
    
    This service connects to the same Redis instance as the main application
    to invalidate cached data when updates are made through the Admin Panel.
    """
    
    def __init__(self):
        """Initialize Redis client with the same configuration as main application"""
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.cache_available = True
            logger.info(f"Cache invalidation service initialized (Redis: {redis_host}:{redis_port}/{redis_db})")
        except (redis.RedisError, Exception) as e:
            logger.error(f"Redis connection failed: {e}. Cache invalidation DISABLED.")
            self.cache_available = False
            self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """
        Generate a consistent cache key from arguments.
        This matches the key generation logic in the main application's redis_cache_service.py
        """
        key_parts = [str(arg) for arg in args if arg is not None]
        key_string = ":".join(key_parts)
        
        # Use hash for very long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
            
        return f"{prefix}:{key_string}"
    
    def _log_invalidation(self, cache_type: str, details: str):
        """Log cache invalidation for debugging"""
        logger.debug(f"[CACHE] Invalidated {cache_type}: {details}")
    
    def invalidate_llm_credentials_for_agent_mappings(
        self, 
        db: Session, 
        llm_credentials_id: int, 
        company_id: Optional[int] = None
    ):
        """
        Invalidate LLM credentials cache for all agent mappings using this credential.
        
        Args:
            db: Database session
            llm_credentials_id: ID of the LLM credentials that changed
            company_id: Optional company_id to filter mappings (if None, invalidates for all companies)
        """
        if not self.cache_available or not self.redis_client:
            return
        
        try:
            # Find all agent mappings using this credential
            query = db.query(AgentMapping).filter(
                AgentMapping.llm_credentials_id == llm_credentials_id
            )
            
            if company_id:
                query = query.filter(AgentMapping.company_id == company_id)
            
            agent_mappings = query.all()
            
            for mapping in agent_mappings:
                agent = mapping.agent
                if agent:
                    # Generate cache key: llm_creds:agent_name:company_id
                    cache_key = self._generate_cache_key("llm_creds", agent.name, mapping.company_id)
                    
                    # Delete the cache key
                    self.redis_client.delete(cache_key)
                    
                    self._log_invalidation(
                        "LLM Credentials",
                        f"agent={agent.name}, company_id={mapping.company_id}, key={cache_key}"
                    )
            
            logger.info(f"Invalidated LLM credentials cache for {len(agent_mappings)} agent mappings")
            
        except Exception as e:
            logger.error(f"Error invalidating LLM credentials cache: {e}")
    
    def invalidate_company_agents_cache(self, company_id: int):
        """
        Invalidate company agents cache for a specific company.
        
        Args:
            company_id: ID of the company
        """
        if not self.cache_available or not self.redis_client:
            return
        
        try:
            # Invalidate all agent types for this company
            pattern = self._generate_cache_key("company_agents", company_id, "*")
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.debug(f"Cleared {len(keys)} company agent cache keys for company {company_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating company agents cache: {e}")
    
    def invalidate_child_agents_cache(self, db: Session, agent_id: int, company_id: int):
        """
        Invalidate child agents cache if the agent has children.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            company_id: ID of the company
        """
        if not self.cache_available or not self.redis_client:
            return
        
        try:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                # Generate cache key: child_agents:company_id:parent_agent_name
                cache_key = self._generate_cache_key("child_agents", company_id, agent.name)
                
                # Delete the cache key
                self.redis_client.delete(cache_key)
                
                self._log_invalidation(
                    "Child Agents",
                    f"parent_agent={agent.name}, company_id={company_id}, key={cache_key}"
                )
                
        except Exception as e:
            logger.error(f"Error invalidating child agents cache: {e}")
    
    def invalidate_all_company_caches(self, db: Session, company_id: int):
        """
        Invalidate all caches related to a company.
        This is used when a company is updated or deleted.
        
        Args:
            db: Database session
            company_id: ID of the company
        """
        if not self.cache_available or not self.redis_client:
            return
        
        try:
            # 1. Invalidate company agents cache
            self.invalidate_company_agents_cache(company_id)
            
            # 2. Invalidate LLM credentials cache for all agents in this company
            agent_mappings = db.query(AgentMapping).filter(
                AgentMapping.company_id == company_id
            ).all()
            
            for mapping in agent_mappings:
                agent = mapping.agent
                if agent:
                    # Generate cache key: llm_creds:agent_name:company_id
                    cache_key = self._generate_cache_key("llm_creds", agent.name, company_id)
                    
                    # Delete the cache key
                    self.redis_client.delete(cache_key)
                    
                    self._log_invalidation(
                        "LLM Credentials",
                        f"agent={agent.name}, company_id={company_id}, key={cache_key}"
                    )
            
            # 3. Invalidate child agents cache for all parent agents in this company
            # Find all agents that have children and are mapped to this company
            subquery = db.query(Agent.parent_agent_id).filter(
                Agent.parent_agent_id.isnot(None)
            ).distinct().subquery()
            
            parent_agents = db.query(Agent).join(AgentMapping).filter(
                AgentMapping.company_id == company_id,
                Agent.id.in_(subquery)  # Only agents that are parents
            ).all()
            
            for parent_agent in parent_agents:
                # Generate cache key: child_agents:company_id:parent_agent_name
                cache_key = self._generate_cache_key("child_agents", company_id, parent_agent.name)
                
                # Delete the cache key
                self.redis_client.delete(cache_key)
                
                self._log_invalidation(
                    "Child Agents",
                    f"parent_agent={parent_agent.name}, company_id={company_id}, key={cache_key}"
                )
            
            logger.info(f"Invalidated all caches for company_id={company_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating all company caches: {e}")
    
    def invalidate_agent_mapping_caches(self, db: Session, agent_id: int, company_id: int):
        """
        Invalidate caches related to a specific agent mapping.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            company_id: ID of the company
        """
        if not self.cache_available or not self.redis_client:
            return
        
        try:
            deleted_keys = []
            
            # 1. Invalidate company agents cache
            self.invalidate_company_agents_cache(company_id)
            
            # 2. Invalidate LLM credentials cache for this specific agent
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                # Delete LLM credentials cache
                cache_key = self._generate_cache_key("llm_creds", agent.name, company_id)
                if self.redis_client.delete(cache_key):
                    deleted_keys.append(cache_key)
                
                # 3. If this agent has children, invalidate child agents cache
                children_count = db.query(Agent).filter(Agent.parent_agent_id == agent.id).count()
                if children_count > 0:
                    cache_key = self._generate_cache_key("child_agents", company_id, agent.name)
                    if self.redis_client.delete(cache_key):
                        deleted_keys.append(cache_key)
                
                # 4. If this agent has a parent, invalidate parent's child agents cache
                if agent.parent_agent_id:
                    parent_agent = db.query(Agent).filter(Agent.id == agent.parent_agent_id).first()
                    if parent_agent:
                        cache_key = self._generate_cache_key("child_agents", company_id, parent_agent.name)
                        if self.redis_client.delete(cache_key):
                            deleted_keys.append(cache_key)
                
                if deleted_keys:
                    logger.info(f"Cleared cache for agent '{agent.name}' (company {company_id}): {len(deleted_keys)} keys")
            
        except Exception as e:
            logger.error(f"Error invalidating agent mapping caches: {e}")


# Global instance
cache_invalidation_service = CacheInvalidationService()

