import os
import redis
from dotenv import load_dotenv
import json
from app.utils.logger import logger

# Load environment variables from .env
load_dotenv()

# Time-to-live for session keys (default: 4 days)
ttl = int(os.getenv("TTL", 345600))

# Configure Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True  # auto-decode bytes to str
)

def save_session_data(session_id: str, data: dict, app_name: str = None):
    """
    Save key-value pairs for a given session ID (Redis hash). 
    If app_name is provided, the key will be session:{session_id}:{app_name}
    `data` must be a dictionary of string -> string.
    """
    if not isinstance(data, dict):
        raise ValueError("Data passed to save_session_data must be a dictionary.")

    try:
        key = f"session:{session_id}"
        if app_name:
            key = f"session:{session_id}:{app_name}"

        # Capture existing state for change logging
        key_existed_before = redis_client.exists(key) == 1
        previous_data = redis_client.hgetall(key) if key_existed_before else {}

        # Compute diffs limited to provided keys (hset does not delete absent fields)
        added_fields = [k for k in data.keys() if k not in previous_data]
        updated_fields = [k for k, v in data.items() if k in previous_data and previous_data.get(k) != v]

        redis_client.hset(key, mapping=data)
        redis_client.expire(key, ttl)

        # Log summary of changes
        if not key_existed_before:
            logger.info(
                f"Created new session hash key='{key}' with {len(data)} fields; ttl={ttl}s"
            )
        else:
            logger.info(
                f"Updated session hash key='{key}': added={len(added_fields)} {added_fields}, updated={len(updated_fields)} {updated_fields}; ttl refreshed to {ttl}s"
            )
    except redis.RedisError as e:
        logger.error(f"Redis error in save_session_data: {e}")
        raise

def get_session_data(session_id: str, app_name: str = None) -> dict:
    """Retrieve all data for a given session ID as a dictionary.
    If app_name is provided, the key will be session:{session_id}:{app_name}
    For backward compatibility, if app_name is provided but no data found, 
    it will fall back to checking the base session key.
    """
    try:
        key = f"session:{session_id}"
    
        if app_name:
            key = f"session:{session_id}:{app_name}"
            # Try app-specific key first, then fall back to base session key
            data = redis_client.hgetall(key)
            if not data:  # If no data found in app-specific key, try base session
                data = redis_client.hgetall(f"session:{session_id}")
            return data
        else:
            return redis_client.hgetall(key)
    except redis.RedisError as e:
        logger.error(f"Redis error in get_session_data: {e}")
        return {}

def delete_session_data(session_id: str, app_name: str = None):
    """Delete all data for a given session ID."""
    try:
        key = f"session:{session_id}"
        if app_name:
            key = f"session:{session_id}:{app_name}"
        
        if redis_client.exists(key) == 1:
            field_count = redis_client.hlen(key)
            redis_client.delete(key)
            logger.info(f"Deleted session hash key='{key}' (removed fields={field_count})")
        else:
            # If app-specific key doesn't exist, try to delete the base session
            base_key = f"session:{session_id}"
            if redis_client.exists(base_key) == 1:
                field_count = redis_client.hlen(base_key)
                redis_client.delete(base_key)
                logger.info(f"Deleted base session hash key='{base_key}' (removed fields={field_count}) after missing '{key}'")
    except redis.RedisError as e:
        logger.error(f"Redis error in delete_session_data: {e}")
        raise
