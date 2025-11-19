import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.db_models import UserSession, SessionHistory, UserFeedback
from app.services.llm_engine import get_llm_credentials_based_on_company_id
from app.utils.logger import logger
import re
from typing import List, Dict
from openai import OpenAI
import os 
from app.utils.datetime import get_formatted_timestamp
from dotenv import load_dotenv
from sqlalchemy import or_
load_dotenv()


# Generates a short summary for a session's chat using an LLM.
async def get_session_chat_summary(response: str, origin: str, company_id: str, app_name: str = None) -> str:
    try:
        prompt = (
            f"Summarize the following bot reply in 3-4 simple words: {response}"
        )
        custom_model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id(app_name, company_id, origin)

        model_name = custom_model.split("/", 1)[-1]

        client = OpenAI(
            base_url=llm_base_url,  
            api_key=llm_key
        )

        response = client.responses.create(
            model=model_name,
            input=prompt
        )
        logger.debug(f"summary tag generated {response.output_text}")
        return response.output_text

    except Exception as e:
        logger.warning(f"OpenAI completion failed: {e}")
        return "Processing your request..."
    

#
# Extracts a preview summary from a structured LLM response for display.
#

async def summarize_text(response: str, origin: str, company_id: str, word_limit: int = 3, app_name: str = None) -> str:
    last_summary_preview = "Just a simple greeting."
    
    try:
        response_dict = json.loads(response)
        if not isinstance(response_dict, dict):
            response_dict = {"response_type": response}
    except (json.JSONDecodeError, TypeError):
        response_dict = {"response_type": response}

    response_type = response_dict.get('response_type')

    if response_type == "table":
        last_summary_preview = response_dict.get(
            'summary',
            "Here’s a list of matching candidates."
        )

    elif response_type == "card":
        last_summary_preview = response_dict.get(
            'full_response',
            "Summary card based on your query."
        )
    else:
        if response_dict.get('full_response'):
            last_summary_preview = response_dict.get('full_response')
        else:
            last_summary_preview = response
        
    return await get_session_chat_summary(json.dumps(last_summary_preview), origin, company_id, app_name)


#
# Creates a new user session in the database and initializes its chat history.
#
def create_user_session(db: Session, user_id: str, session_id: str, app_name:str = None, mode:str = None) -> dict:
    now = datetime.now(timezone.utc)  # UTC with timezone info
    logger.info(f"Creating new UserSession for user_id={user_id}, session_id={session_id}, mode={mode}")

    user_session = UserSession(
        user_id=user_id,
        session_id=session_id,
        app_name=app_name,
        mode=mode,
        created_at=now,
        last_summary=""
    )
    db.add(user_session)
    db.commit()

    logger.info(f"UserSession created with session_id={session_id}")

    session_history = SessionHistory(session_id=session_id, history="[]")
    db.add(session_history)
    db.commit()

    logger.info(f"SessionHistory created for session_id={session_id}")

    return {
        "created_at": now.isoformat(),
        "history": "[]",
        "last_summary": ""
    }


#
# Appends to and updates the session's chat history and updates the summary if needed.
#
async def update_user_session_history(
    db: Session,
    session_id: str,
    user_query: str,
    assistant_reply: str,
    event_id: str,
    origin: str,
    company_id: str,
    app_name: str = None
):
    logger.info(f"Updating session history for session_id={session_id}")
    # Try to fetch session history with a row lock
    session_history = (
        db.query(SessionHistory)
        .filter_by(session_id=session_id)
        .with_for_update()
        .first()
    )
    ts = get_formatted_timestamp()
    # TODO: @ishan user timestamp and response timestamp can be same.
    if not session_history:
        print("First message in this session")
        # First message in this session
        history = [
            {"role": "user", "content": user_query, "event_id": event_id, "timestamp": ts},
            {"role": "assistant", "content": assistant_reply, "event_id": event_id, "timestamp": ts}
        ]
        session_history = SessionHistory(session_id=session_id, history=json.dumps(history))
        db.add(session_history)

    else:
        # Not the first message, append to history
        try:
            history = json.loads(session_history.history)
            if not isinstance(history, list):
                history = []
        except json.JSONDecodeError:
            history = []

        base_query = db.query(UserSession).filter(UserSession.session_id == session_id)
        if app_name:
            base_query = base_query.filter(
                or_(
                    UserSession.app_name == app_name,
                    UserSession.app_name == None,
                    UserSession.app_name == ''
                )
            )
        user_session = base_query.first()
        # Backfill app_name on old records if provided and missing
        if user_session and app_name and (user_session.app_name is None or user_session.app_name == ''):
            user_session.app_name = app_name

        if user_session and not user_session.is_renamed:
            if len(history) < 4:
                summary = "Temporary chat"
                if user_session:
                    user_session.last_summary = summary
                logger.info("Session summary set for temp chat")
            elif len(history) == 4:
                summary = await summarize_text(assistant_reply, origin, company_id, app_name=app_name)
                if user_session:
                    user_session.last_summary = summary
                logger.info("Session summary set")
        else:
            logger.info(f"Session {session_id} is renamed — skipping summary update.")

        history.append({"role": "user", "content": user_query, "event_id": event_id, "timestamp": ts})
        history.append({"role": "assistant", "content": assistant_reply, "event_id": event_id, "timestamp": ts})
        session_history.history = json.dumps(history)

    db.commit()
    logger.info(f"Session history updated for session_id={session_id}")

#
# Returns paginated user sessions for a given user.
#
def list_user_sessions(db: Session, user_id: str, limit: int = 10, offset: int = 0, app_name: str = None) -> dict:
    query = db.query(UserSession).filter(UserSession.user_id == user_id)
    if app_name:
        query = query.filter(
            or_(
                UserSession.app_name == app_name,
                UserSession.app_name == None,
                UserSession.app_name == ''
            )
        )
    query = query.order_by(UserSession.created_at.desc())

    total = query.count()  # total number of sessions for the user
    sessions = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "page": (offset // limit) + 1,
        "sessions": [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "last_summary": s.last_summary or ""
            } for s in sessions
        ]
    }


#
# Renames a chat session for the sidebar display.
#
def rename_chatname(db: Session, user_id:str, session_id: str, chat_name: str, app_name: str = None):
    base_query = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.session_id == session_id,
    )
    if app_name:
        base_query = base_query.filter(
            or_(
                UserSession.app_name == app_name,
                UserSession.app_name == None,
                UserSession.app_name == ''
            )
        )
    session = base_query.first()

    if not session:
        logger.error(f"No such session exist with session_id: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    last_name = session.last_summary
    session.is_renamed = True
    session.last_summary = chat_name
    logger.info(f"chat renamed successfully with name:{chat_name}")

    db.commit()

    return {
        "session_id": session.session_id,
        "last_name" : last_name,
        "chat_name": session.last_summary,
    }
    

#
# Fetches detailed information and paginated history for a specific user session.
#
def get_user_session_details(
    db: Session,
    user_id: str,
    session_id: str,
    limit: int = 2,
    offset: int = 0,
    app_name: str = None
) -> Dict:
    # Fetch the user's session
    query = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.session_id == session_id,
    )
    if app_name:
        query = query.filter(
            or_(
                UserSession.app_name == app_name,
                UserSession.app_name == None,
                UserSession.app_name == ''
            )
        )
    user_session = query.first()
    if not user_session:
        raise HTTPException(status_code=404, detail=f"Session not found for user {user_id} and session_id {session_id}")

    # Fetch session history from DB
    session_history = db.query(SessionHistory).filter_by(session_id=session_id).first()
    full_history = json.loads(session_history.history) if session_history and session_history.history else []

    # Deserialize 'content' if it's a string
    for entry in full_history:
        content = entry.get("content")
        if isinstance(content, str):
            try:
                entry["content"] = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                # Leave it as string if it's not valid JSON
                pass

    # Apply pagination
    total = len(full_history)
    paginated_history = full_history[offset:offset + limit]

    return {
        "session_id": user_session.session_id,
        "created_at": user_session.created_at.isoformat(),
        "last_summary": user_session.last_summary or "",
        "history": paginated_history,
        "pagination": {
            "total": total,
            "limit": limit,
            "page": (offset // limit) + 1
        }
    }


#
# Searches within all chat session histories for a user for a given keyword.
#
def search_chat_history(db: Session, user_id: str, keyword: str, limit: int = 10, offset: int = 0, app_name: str = None) -> Dict:
    matched_snippets: List[Dict] = []

    # Get all session_ids for this user
    session_query = db.query(UserSession.session_id).filter(UserSession.user_id == user_id)
    if app_name:
        session_query = session_query.filter(
            or_(
                UserSession.app_name == app_name,
                UserSession.app_name == None,
                UserSession.app_name == ''
            )
        )
    session_ids = [sid[0] for sid in session_query.all()]

    if not session_ids:
        return {
            "total": 0,
            "results": [],
            "limit": limit,
            "page": (offset // limit) + 1
        }

    # Fetch histories for all sessions
    histories = db.query(SessionHistory).filter(SessionHistory.session_id.in_(session_ids)).all()

    for history_record in histories:
        session_id = history_record.session_id
        us_query = db.query(UserSession).filter(UserSession.session_id == session_id)
        if app_name:
            us_query = us_query.filter(
                or_(
                    UserSession.app_name == app_name,
                    UserSession.app_name == None,
                    UserSession.app_name == ''
                )
            )
        us_row = us_query.first()
        last_summary = us_row.last_summary if us_row else ""
        try:
            history_items = json.loads(history_record.history)
        except Exception:
            continue  

        for item in reversed(history_items):
            content = item.get("content", "")
            if keyword.lower() in content.lower():
                matched_snippets.append({
                    "session_id": session_id,
                    "role": item.get("role"),
                    "content": content,
                    "timestamp":item.get("timestamp"),
                    "last_summary":last_summary
                })
                break  

    total = len(matched_snippets)
    paginated = matched_snippets[offset:offset + limit]

    return {
        "total": total,
        "limit": limit,
        "page": (offset // limit) + 1,
        "results": paginated
    }


#
# Checks if a session exists, optionally filtered by app_name.
#
def check_existing_session(db: Session, session_id: str, app_name: str | None = None, mode: str = None) -> UserSession:
    base = db.query(UserSession).filter(UserSession.session_id == session_id)
    return base.first()


async def update_thumbs_up_down_count(
    db: Session,
    session_id: str,
    thumbs_up: int,
    thumbs_down: int,
    message_id: str | None = None,
    company_id: str | None = None,
    origin: str | None = None,
):
    """
    Record user feedback for a specific message in a chat session.

    Persists a row in the 'user_feedback' table with message_id, company_id,
    origin, session_id and the thumbs counts.
    """
    try:
        feedback = UserFeedback(
            session_id=session_id,
            message_id=message_id or "",
            company_id=str(company_id) if company_id is not None else None,
            origin=origin,
            thumbs_up=int(thumbs_up or 0),
            thumbs_down=int(thumbs_down or 0),
        )
        db.add(feedback)
        db.commit()
        return {
            "status": "success",
            "session_id": session_id,
            "message_id": message_id,
            "company_id": company_id,
            "origin": origin,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record user feedback: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Failed to record feedback",
        }