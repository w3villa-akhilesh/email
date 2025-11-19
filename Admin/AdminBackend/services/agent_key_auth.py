import re
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from database.models import AgentApiKey


def verify_agent_api_key_and_app(db: Session, api_key: str) -> Dict:
    """
    Verify authenticity of an agent API key by:
      1) Decrypting the key
      2) Extracting the app name from plaintext format: <prefix>|<app>|<sr>|<rand>
      3) Matching the encrypted value and app against the database record

    Args:
        db: SQLAlchemy session
        encrypted_key: API key value received from the client (encrypted)

    Returns:
        Dict with record metadata: { id, client_app_name }

    Raises:
        HTTPException 401: If key is invalid/inactive or app mismatch
    """
    # 1) Extract app name from plaintext
    # Prefer '-' delimiters; fallback to '|' or '_' for older keys
    if '-' in api_key:
        parts = api_key.split('-')
        joiner = '-'
        min_parts = 3  # w3-<app>-<rand>
    elif '|' in api_key:
        parts = api_key.split('|')
        joiner = '|'
        min_parts = 4
    else:
        parts = api_key.split('_')
        joiner = '_'
        min_parts = 4
    if len(parts) < min_parts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed API key")

    # Support app names that may include the delimiter by joining middle segments
    prefix = parts[0]
    if joiner == '-':
        # New format without SR: w3-<app>-<rand>
        app_slug = joiner.join(parts[1:-1])
    else:
        # Legacy formats with SR in the second last position
        app_slug = joiner.join(parts[1:-2])
    if not app_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed API key")

    # 2) Match plaintext key and app against DB
    record = (
        db.query(AgentApiKey)
        .filter(AgentApiKey.api_key == api_key, AgentApiKey.is_active == True)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive API key")

    # Normalize stored app name for comparison to slug from key
    normalized_db_app = re.sub(r"(^-|-$)+", "", re.sub(r"[^a-z0-9]+", "-", (record.client_app_name or "").strip().lower()))
    if normalized_db_app != app_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key app mismatch")

    return {
        "id": record.id,
        "client_app_name": record.client_app_name,
    }
