import os
import redis
import json
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from dotenv import load_dotenv
from app.utils.logger import logger
from app.models.db_models import Agent, LLMCredentials

# Load environment variables
load_dotenv()

class RedisCacheService:
    """
    Comprehensive Redis caching service for LLM credentials and agent mappings
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True
        )
        
        # Cache TTL settings (in seconds)
        self.llm_credentials_ttl = int(os.getenv("LLM_CREDENTIALS_CACHE_TTL", 86400))  # 24 hours
        self.agent_mappings_ttl = int(os.getenv("AGENT_MAPPINGS_CACHE_TTL", 86400))    # 24 hours
        self.child_agents_ttl = int(os.getenv("CHILD_AGENTS_CACHE_TTL", 86400))        # 24 hours
        
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate a consistent cache key from arguments"""
        key_parts = [str(arg) for arg in args if arg is not None]
        key_string = ":".join(key_parts)
        
        logger.debug(f"Generating cache key with prefix '{prefix}' and arguments {args}")
        
        # Use hash for very long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            generated_key = f"{prefix}:hash:{key_hash}"
            logger.debug(f"Generated hash key: {generated_key}")
            return generated_key
            
        generated_key = f"{prefix}:{key_string}"
        logger.debug(f"Generated cache key: {generated_key}")
        return generated_key
    
    def _serialize_agent_list(self, agents: List[Agent]) -> str:
        """Serialize a list of Agent objects for caching"""
        agent_data = []
        for agent in agents:
            agent_dict = {
                'id': agent.id,
                'name': agent.name,
                'agent_type': agent.agent_type,
                'description': agent.description,
                'is_active': agent.is_active,
                'parent_agent_id': agent.parent_agent_id,
                'created_at': agent.created_at.isoformat() if agent.created_at else None,
                'updated_at': agent.updated_at.isoformat() if agent.updated_at else None
            }
            agent_data.append(agent_dict)
        return json.dumps(agent_data)
    
    def _deserialize_agent_list(self, cached_data: str) -> List[Dict]:
        """Deserialize cached agent data back to dictionaries (not full Agent objects to avoid DB session issues)"""
        try:
            return json.loads(cached_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to deserialize cached agent data")
            return []
    
    # LLM Credentials Caching
    def cache_llm_credentials(self, agent_name: str, company_id: int, model: str, api_key: str, base_url: str):
        """Cache LLM credentials for an agent and company"""
        try:
            cache_key = self._generate_cache_key("llm_creds", agent_name, company_id)
            credentials_data = {
                'model': model,
                'api_key': api_key,  # Note: This should already be decrypted when cached
                'base_url': base_url,
                'cached_at': str(os.times().elapsed)
            }
            
            self.redis_client.hset(cache_key, mapping=credentials_data)
            self.redis_client.expire(cache_key, self.llm_credentials_ttl)
            
            logger.debug(f"Cached LLM credentials for agent '{agent_name}' and company {company_id}")
            
        except redis.RedisError as e:
            logger.error(f"Failed to cache LLM credentials: {e}")
    
    def get_cached_llm_credentials(self, agent_name: str, company_id: int) -> Optional[Tuple[str, str, str]]:
        """Retrieve cached LLM credentials"""
        try:
            cache_key = self._generate_cache_key("llm_creds", agent_name, company_id)

            logger.debug(f"Retrieving cached LLM credentials for agent '{agent_name}' and company {company_id}")
            
            cached_data = self.redis_client.hgetall(cache_key)
            logger.debug(f"Cached data: {cached_data}")

            if cached_data and all(key in cached_data for key in ['model', 'api_key', 'base_url']):
                logger.debug(f"Retrieved LLM credentials from cache for agent '{agent_name}' and company {company_id}")
                return cached_data['model'], cached_data['api_key'], cached_data['base_url']
            
            return None
            
        except redis.RedisError as e:
            logger.error(f"Failed to retrieve cached LLM credentials: {e}")
            return None
    
    def invalidate_llm_credentials(self, agent_name: str, company_id: int):
        """Invalidate cached LLM credentials"""
        try:
            cache_key = self._generate_cache_key("llm_creds", agent_name, company_id)
            self.redis_client.delete(cache_key)
            logger.debug(f"Invalidated LLM credentials cache for agent '{agent_name}' and company {company_id}")
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate LLM credentials cache: {e}")
    
    # Company Agents Caching
    def cache_company_agents(self, company_id: int, agent_type: Optional[str], agents: List[Agent]):
        """Cache company agents"""
        try:
            cache_key = self._generate_cache_key("company_agents", company_id, agent_type or "all")
            serialized_agents = self._serialize_agent_list(agents)
            
            self.redis_client.set(cache_key, serialized_agents, ex=self.agent_mappings_ttl)
            
            logger.debug(f"Cached {len(agents)} agents for company {company_id}, type: {agent_type or 'all'}")
            
        except redis.RedisError as e:
            logger.error(f"Failed to cache company agents: {e}")
    
    def get_cached_company_agents(self, company_id: int, agent_type: Optional[str] = None) -> Optional[List[Dict]]:
        """Retrieve cached company agents"""
        try:
            cache_key = self._generate_cache_key("company_agents", company_id, agent_type or "all")
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                agents_data = self._deserialize_agent_list(cached_data)
                logger.debug(f"Retrieved {len(agents_data)} agents from cache for company {company_id}, type: {agent_type or 'all'}")
                return agents_data
            
            return None
            
        except redis.RedisError as e:
            logger.error(f"Failed to retrieve cached company agents: {e}")
            return None
    
    def invalidate_company_agents(self, company_id: int, agent_type: Optional[str] = None):
        """Invalidate cached company agents"""
        try:
            if agent_type:
                # Invalidate specific agent type
                cache_key = self._generate_cache_key("company_agents", company_id, agent_type)
                self.redis_client.delete(cache_key)
            else:
                # Invalidate all agent types for this company
                pattern = self._generate_cache_key("company_agents", company_id, "*")
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            logger.debug(f"Invalidated company agents cache for company {company_id}, type: {agent_type or 'all'}")
            
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate company agents cache: {e}")
    
    # Child Agents Caching
    def cache_child_agents(self, company_id: int, parent_agent_name: str, child_agent_names: List[str]):
        """Cache child agent names for a parent agent"""
        try:
            cache_key = self._generate_cache_key("child_agents", company_id, parent_agent_name)
            child_agents_data = json.dumps(child_agent_names)
            
            self.redis_client.set(cache_key, child_agents_data, ex=self.child_agents_ttl)
            
            logger.debug(f"Cached {len(child_agent_names)} child agents for parent '{parent_agent_name}' in company {company_id}")
            
        except redis.RedisError as e:
            logger.error(f"Failed to cache child agents: {e}")
    
    def get_cached_child_agents(self, company_id: int, parent_agent_name: str) -> Optional[List[str]]:
        """Retrieve cached child agent names"""
        try:
            cache_key = self._generate_cache_key("child_agents", company_id, parent_agent_name)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                child_agent_names = json.loads(cached_data)
                logger.debug(f"Retrieved {len(child_agent_names)} child agents from cache for parent '{parent_agent_name}' in company {company_id}")
                return child_agent_names
            
            return None
            
        except redis.RedisError as e:
            logger.error(f"Failed to retrieve cached child agents: {e}")
            return None
    
    def invalidate_child_agents(self, company_id: int, parent_agent_name: str):
        """Invalidate cached child agents"""
        try:
            cache_key = self._generate_cache_key("child_agents", company_id, parent_agent_name)
            self.redis_client.delete(cache_key)
            logger.debug(f"Invalidated child agents cache for parent '{parent_agent_name}' in company {company_id}")
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate child agents cache: {e}")
    
    # Cache Management
    def clear_all_agent_cache(self):
        """Clear all agent-related cache"""
        try:
            patterns = ["llm_creds:*", "company_agents:*", "child_agents:*"]
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            logger.info("Cleared all agent-related cache")
            
        except redis.RedisError as e:
            logger.error(f"Failed to clear agent cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats = {
                'llm_credentials_keys': len(self.redis_client.keys("llm_creds:*")),
                'company_agents_keys': len(self.redis_client.keys("company_agents:*")),
                'child_agents_keys': len(self.redis_client.keys("child_agents:*")),
                'redis_info': self.redis_client.info('memory')
            }
            return stats
        except redis.RedisError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

# Global cache service instance
cache_service = RedisCacheService()

# Convenience functions for backward compatibility
def cache_result(cache_key: str, ttl: int = 3600):
    """Decorator for caching function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Try to get from cache first
                cached_result = cache_service.redis_client.get(cache_key)
                if cached_result:
                    logger.debug(f"Retrieved result from cache for key: {cache_key}")
                    return json.loads(cached_result)
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache_service.redis_client.set(cache_key, json.dumps(result), ex=ttl)
                logger.debug(f"Cached result for key: {cache_key}")
                return result
                
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.error(f"Cache operation failed for key {cache_key}: {e}")
                # Fallback to executing function without cache
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
