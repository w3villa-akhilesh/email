import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from routers.auth import get_token, validate_token
from schemas import AgentKeyCreate
from services.generate_agent_key import create_agent_api_key
from services.agent_keys_service import get_agent_keys_list, delete_agent_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-keys", tags=["agent-keys"])


@router.post("")
def generate_agent_api_key(
    payload: AgentKeyCreate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Generate and persist an API key for a client application.
    Requires a valid access token.
    """
    try:
        validate_token(access_token)
        created = create_agent_api_key(
            db=db,
            client_app_name=payload.app_name,
        )

        return JSONResponse(content={
            "status": "success",
            "message": "Agent API key generated successfully",
            "data": created,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_agent_api_key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("")
def list_agent_api_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    app_name: Optional[str] = None,
    status: Optional[str] = None,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of agent API keys with optional filters.
    Requires a valid access token.
    """
    try:
        validate_token(access_token)
        result = get_agent_keys_list(
            db=db,
            app_name=app_name,
            status=status,
            page=page,
            page_size=page_size,
        )
        return JSONResponse(content={
            'status': 'success',
            'message': 'Agent API keys fetched successfully',
            'data': result,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_agent_api_keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{key_id}")
def delete_agent_api_key(
    key_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Delete an agent API key by ID.
    Requires a valid access token.
    """
    try:
        validate_token(access_token)
        success = delete_agent_key(db, key_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent API key not found")
        return JSONResponse(content={
            'status': 'success',
            'message': 'Agent API key deleted successfully',
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_agent_api_key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

