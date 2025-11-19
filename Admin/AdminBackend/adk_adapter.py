"""
ADK Adapter for Kivo Agents
This module provides ADK-compatible API endpoints that translate to Kivo's backend.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from database.connection import get_db
from database.models import Event
from sqlalchemy import distinct, func

logger = logging.getLogger(__name__)


def register_adk_routes(app: FastAPI):
    """Register ADK-compatible routes on the FastAPI app."""
    
    # Import authentication functions from the auth router
    from routers.auth import get_token, validate_token
    
    @app.get("/list-apps")
    async def list_apps(
        relative_path: str = "./",
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        List all available apps (agents) from the Kivo system.
        Maps to: Available app names from the events table.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            # Query unique app names from Event table
            app_names_query = db.query(distinct(Event.app_name)).all()
            app_names = [row[0] for row in app_names_query if row[0] is not None]
            
            logger.info(f"ADK Adapter: Listed {len(app_names)} apps")
            return JSONResponse(content=app_names)
            
        except Exception as e:
            logger.error(f"Error in list-apps: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/apps/{app_name}/users/{user_id}/sessions")
    async def list_sessions(
        app_name: str,
        user_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        List all sessions for a specific user and app.
        Returns sessions in ADK format.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            # Query unique sessions from Event table
            sessions_query = db.query(
                Event.session_id,
                func.max(Event.timestamp).label('last_update'),
                func.count(Event.id).label('event_count')
            ).filter(
                Event.app_name == app_name,
                Event.user_id == user_id
            ).group_by(Event.session_id).order_by(func.max(Event.timestamp).desc()).all()
            
            # Convert to ADK format
            adk_sessions = []
            for session in sessions_query:
                adk_sessions.append({
                    "id": session.session_id,
                    "appName": app_name,
                    "userId": user_id,
                    "state": {},
                    "events": [],  # Events loaded separately
                    "lastUpdateTime": int(session.last_update.timestamp() * 1000) if session.last_update else 0,
                    "eventCount": session.event_count
                })
            
            logger.info(f"ADK Adapter: Listed {len(adk_sessions)} sessions for {app_name}/{user_id}")
            return JSONResponse(content=adk_sessions)
            
        except Exception as e:
            logger.error(f"Error in list-sessions: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
    async def get_session(
        app_name: str,
        user_id: str,
        session_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        Get a specific session with all its events in ADK format.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            # Handle URL encoding: + becomes space in URL decoding, restore it
            session_id = session_id.strip().replace(" ", "+")
            # Get all events for this session (removed app_name filter to match all events)
            events = db.query(Event).filter(
                Event.session_id == session_id
            ).order_by(Event.timestamp.asc()).all()
            
            if not events:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert events to ADK format
            adk_events = []
            for event in events:
                adk_event = convert_kivo_event_to_adk(event)
                adk_events.append(adk_event)
            
            # Get last update time from events
            last_update = max([e.timestamp for e in events if e.timestamp])
            
            # Build session response
            session_data = {
                "id": session_id,
                "appName": app_name,
                "userId": user_id,
                "state": {},
                "events": adk_events,
                "lastUpdateTime": int(last_update.timestamp() * 1000) if last_update else 0
            }
            
            logger.info(f"ADK Adapter: Retrieved session {session_id} with {len(adk_events)} events")
            return JSONResponse(content=session_data)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get-session: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.post("/apps/{app_name}/users/{user_id}/sessions")
    async def create_session(
        app_name: str,
        user_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        Create a new session.
        Note: Without a UserSession table, this just returns a session object.
        Events will be created when the ADK UI actually runs the agent.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            import uuid
            from datetime import datetime
            
            # Generate new session ID
            new_session_id = f"adk_session_{uuid.uuid4().hex}"
            
            session_data = {
                "id": new_session_id,
                "appName": app_name,
                "userId": user_id,
                "state": {},
                "events": [],
                "lastUpdateTime": int(datetime.utcnow().timestamp() * 1000)
            }
            
            logger.info(f"ADK Adapter: Created new session {new_session_id}")
            return JSONResponse(content=session_data)
            
        except Exception as e:
            logger.error(f"Error in create-session: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
    async def delete_session(
        app_name: str,
        user_id: str,
        session_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        Delete a session by deleting all its events.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            # Delete all events for this session
            deleted_count = db.query(Event).filter(
                Event.session_id == session_id,
                Event.app_name == app_name
            ).delete()
            
            db.commit()
            
            if deleted_count == 0:
                raise HTTPException(status_code=404, detail="Session not found")
            
            logger.info(f"ADK Adapter: Deleted session {session_id} ({deleted_count} events)")
            return JSONResponse(content={"status": "success", "message": "Session deleted"})
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in delete-session: {str(e)}", exc_info=True)
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/debug/trace/{event_id}")
    async def get_event_trace(
        event_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        Get trace data for a specific event.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            # Try to find by id (convert to int if it's a number)
            try:
                event_id_int = int(event_id)
                event = db.query(Event).filter(Event.id == event_id_int).first()
            except ValueError:
                # If not a number, try invocation_id
                event = db.query(Event).filter(Event.invocation_id == event_id).first()
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            trace_data = {
                "eventId": str(event.id),
                "timestamp": int(event.timestamp.timestamp() * 1000) if event.timestamp else None,
                "author": event.author,
                "invocationId": event.invocation_id,
                "content": event.content if event.content else {},
                "appName": event.app_name,
                "sessionId": event.session_id
            }
            
            return JSONResponse(content=trace_data)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get-event-trace: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/debug/trace/session/{session_id}")
    async def get_session_trace(
        session_id: str,
        access_token: str = Depends(get_token),
        db: Session = Depends(get_db)
    ):
        """
        Get trace data for all events in a session.
        Requires authentication.
        """
        try:
            # Validate token
            validate_token(access_token)
            events = db.query(Event).filter(
                Event.session_id == session_id
            ).order_by(Event.timestamp.asc()).all()
            
            if not events:
                raise HTTPException(status_code=404, detail="Session not found or no events")
            
            trace_data = {
                "sessionId": session_id,
                "events": [
                    {
                        "eventId": str(event.id),
                        "timestamp": int(event.timestamp.timestamp() * 1000) if event.timestamp else None,
                        "author": event.author,
                        "invocationId": event.invocation_id,
                        "content": event.content if event.content else {}
                    }
                    for event in events
                ]
            }
            
            return JSONResponse(content=trace_data)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get-session-trace: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


    # Stub endpoints for ADK evaluation features (not implemented in Kivo)
    @app.get("/apps/{app_name}/eval_sets")
    async def get_eval_sets(
        app_name: str,
        access_token: str = Depends(get_token)
    ):
        """Return empty eval sets (not implemented). Requires authentication."""
        validate_token(access_token)
        logger.info(f"ADK Adapter: eval_sets requested for {app_name} (returning empty)")
        return JSONResponse(content=[])

    @app.get("/apps/{app_name}/eval_results")
    async def get_eval_results(
        app_name: str,
        access_token: str = Depends(get_token)
    ):
        """Return empty eval results (not implemented). Requires authentication."""
        validate_token(access_token)
        logger.info(f"ADK Adapter: eval_results requested for {app_name} (returning empty)")
        return JSONResponse(content=[])

    @app.post("/apps/{app_name}/eval_sets")
    async def create_eval_set(
        app_name: str,
        access_token: str = Depends(get_token)
    ):
        """Stub for creating eval sets (not implemented). Requires authentication."""
        validate_token(access_token)
        logger.info(f"ADK Adapter: create_eval_set requested for {app_name} (not implemented)")
        return JSONResponse(content={"status": "not_implemented"}, status_code=501)

    @app.post("/apps/{app_name}/eval_results")
    async def create_eval_result(
        app_name: str,
        access_token: str = Depends(get_token)
    ):
        """Stub for creating eval results (not implemented). Requires authentication."""
        validate_token(access_token)
        logger.info(f"ADK Adapter: create_eval_result requested for {app_name} (not implemented)")
        return JSONResponse(content={"status": "not_implemented"}, status_code=501)


def convert_kivo_event_to_adk(event: Event) -> Dict[str, Any]:
    """
    Convert a Kivo Event to ADK format.
    Enhanced to handle Kivo's actual content structure which uses 'parts' array.
    Also handles agent transfers, system messages, and various content formats.
    """
    import json
    
    # Parse content if it's a JSON string
    content = event.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except:
            content = {"text": content}
    elif content is None:
        content = {}
    
    # Determine role based on author (normalize)
    author_lower = (event.author or "").lower()
    if author_lower == "user":
        role = "user"
    elif author_lower == "system":
        role = "system"
    else:
        # Any agent/assistant/triage-like author is treated as model
        role = "model"
    
    # Build ADK-compatible event
    adk_event = {
        "id": str(event.id),  # Use the integer ID from database
        "author": event.author,
        "invocationId": event.invocation_id,
        "timestamp": int(event.timestamp.timestamp() * 1000) if event.timestamp else None,
        "content": {
            "role": role,
            "parts": []
        }
    }
    
    # Extract parts from content
    if isinstance(content, dict):
        # FIRST: Check if content already has a 'parts' array (Kivo's actual structure)
        if "parts" in content and isinstance(content["parts"], list) and len(content["parts"]) > 0:
            # Normalize existing parts to ADK schema (camelCase function keys)
            normalized_parts = []
            for p in content["parts"]:
                if not isinstance(p, dict) or p == {}:
                    continue
                # Text passthrough
                if "text" in p and p["text"] is not None:
                    normalized_parts.append({"text": p["text"]})
                    continue
                # Normalize function call variants
                if "function_call" in p or "tool_call" in p or "functionCall" in p or "toolCall" in p:
                    raw = p.get("function_call") or p.get("tool_call") or p.get("functionCall") or p.get("toolCall") or {}
                    if isinstance(raw, dict):
                        normalized_parts.append({
                            "functionCall": {
                                "name": raw.get("name", raw.get("function", "")),
                                "args": raw.get("args", raw.get("arguments", {}))
                            }
                        })
                        continue
                # Normalize function response variants
                if "function_response" in p or "tool_response" in p or "functionResponse" in p or "toolResponse" in p:
                    raw = p.get("function_response") or p.get("tool_response") or p.get("functionResponse") or p.get("toolResponse") or {}
                    if isinstance(raw, dict):
                        normalized_parts.append({
                            "functionResponse": {
                                "name": raw.get("name", raw.get("function", "")),
                                "response": raw.get("response", raw.get("result", {}))
                            }
                        })
                        continue
                # Fallback: include raw as pretty JSON text
                try:
                    import json as _json
                    normalized_parts.append({"text": _json.dumps(p, ensure_ascii=False)})
                except Exception:
                    normalized_parts.append({"text": str(p)})

            if normalized_parts:
                adk_event["content"]["parts"] = normalized_parts
            else:
                # Parts array exists but all parts are empty
                adk_event["content"]["parts"].append({"text": _extract_fallback_text(content)})
        else:
            # Legacy format or non-standard structure: extract from various fields
            parts_added = False
            
            # Strategy 1: Check for direct text fields
            text_fields = ["text", "message", "response", "content", "data", "result", "output"]
            for field in text_fields:
                if field in content and content[field]:
                    text_value = content[field]
                    if isinstance(text_value, str) and text_value.strip():
                        adk_event["content"]["parts"].append({"text": text_value})
                        parts_added = True
                        break
                    elif isinstance(text_value, (dict, list)):
                        adk_event["content"]["parts"].append({"text": json.dumps(text_value, indent=2)})
                        parts_added = True
                        break
            
            # Strategy 2: Check for function calls (including agent transfers)
            func_call_fields = ["functionCall", "function_call", "tool_call", "toolCall"]
            for field in func_call_fields:
                if field in content and content[field]:
                    func_call = content[field]
                    if isinstance(func_call, dict):
                        adk_event["content"]["parts"].append({
                            "functionCall": {
                                "name": func_call.get("name", func_call.get("function", "unknown")),
                                "args": func_call.get("args", func_call.get("arguments", {}))
                            }
                        })
                        parts_added = True
            
            # Strategy 3: Check for function responses
            func_resp_fields = ["functionResponse", "function_response", "tool_response", "toolResponse"]
            for field in func_resp_fields:
                if field in content and content[field]:
                    func_resp = content[field]
                    if isinstance(func_resp, dict):
                        adk_event["content"]["parts"].append({
                            "functionResponse": {
                                "name": func_resp.get("name", func_resp.get("function", "unknown")),
                                "response": func_resp.get("response", func_resp.get("result", {}))
                            }
                        })
                        parts_added = True
            
            # Strategy 4: Check for agent transfer specific fields
            if "agent" in content or "transfer_to" in content or "agent_name" in content:
                transfer_target = content.get("agent") or content.get("transfer_to") or content.get("agent_name")
                transfer_text = f"Agent Transfer → {transfer_target}"
                if "reason" in content:
                    transfer_text += f"\nReason: {content['reason']}"
                adk_event["content"]["parts"].append({"text": transfer_text})
                parts_added = True
            
            # Strategy 5: If still nothing, try to extract ANY meaningful content
            if not parts_added:
                fallback_text = _extract_fallback_text(content)
                if fallback_text:
                    adk_event["content"]["parts"].append({"text": fallback_text})
                    parts_added = True
    else:
        # If content is not a dict, treat it as text
        text_content = str(content) if content else None
        if text_content and text_content.strip():
            adk_event["content"]["parts"].append({"text": text_content})
        else:
            adk_event["content"]["parts"].append({"text": "[Empty content]"})
    
    # If no parts were added, show the raw content
    if not adk_event["content"]["parts"]:
        # Log the problematic content for debugging
        logger.warning(f"Event {event.id}: No content extracted. Author: {event.author}, Content keys: {list(content.keys()) if isinstance(content, dict) else 'not a dict'}")
        
        # Show the actual content to help with debugging
        if isinstance(content, dict):
            import json
            
            # Check if dict is empty
            if not content or content == {}:
                adk_event["content"]["parts"].append({
                    "text": f"[Empty Event]\nAuthor: {event.author}\nSession: {event.session_id}\nInvocation: {event.invocation_id}"
                })
            else:
                try:
                    content_str = json.dumps(content, indent=2, ensure_ascii=False)
                    # Limit very large content
                    if len(content_str) > 2000:
                        content_str = content_str[:2000] + "\n... (truncated, too large)"
                    
                    adk_event["content"]["parts"].append({
                        "text": f"[Raw Content - Non-standard format]\nAuthor: {event.author}\nKeys: {', '.join(content.keys())}\n\n{content_str}"
                    })
                except Exception as e:
                    adk_event["content"]["parts"].append({
                        "text": f"[Content Error]\nAuthor: {event.author}\nError: {str(e)}\nContent: {str(content)[:500]}"
                    })
        else:
            adk_event["content"]["parts"].append({
                "text": f"[Non-dict Content]\nAuthor: {event.author}\nType: {type(content).__name__}\nValue: {str(content)[:500]}"
            })
    
    return adk_event


def _extract_fallback_text(content: dict) -> str:
    """
    Extract any meaningful text from a content dict when standard extraction fails.
    This is a fallback to ensure we show SOMETHING rather than [No content].
    """
    import json
    
    if not isinstance(content, dict) or not content:
        return ""
    
    # Try to find any string values in the dict
    text_parts = []
    
    # Check all keys for string values
    for key, value in content.items():
        if key in ["parts"]:  # Skip parts array as it's handled separately
            continue
        if isinstance(value, str) and value.strip():
            text_parts.append(f"{key}: {value}")
        elif isinstance(value, (int, float, bool)):
            text_parts.append(f"{key}: {value}")
        elif isinstance(value, dict) and value:
            # Try to extract from nested dict
            nested_text = _extract_fallback_text(value)
            if nested_text:
                text_parts.append(f"{key}: {nested_text}")
    
    if text_parts:
        return "\n".join(text_parts)
    
    # Last resort: return a JSON dump of the content (limited to first 500 chars)
    try:
        json_str = json.dumps(content, indent=2)
        if len(json_str) > 500:
            return json_str[:500] + "\n... (truncated)"
        return json_str
    except:
        return str(content)[:500]

