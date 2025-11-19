from typing import Dict, Any
import time
from google.adk.sessions import DatabaseSessionService
from google.adk.events import Event, EventActions
from app.services.my_sql_client import create_db_url
from app.services.performance_config_service import get_performance_config
from app.utils.logger import logger
from app.models.schema import (
    EmployeePerformanceData
)


async def _setup_performance_session(
    user_id: str, 
    session_id: str, 
    employee_id: str, 
    app_name: str
) -> Dict[str, Any]:
    """Set up database session service and create/retrieve performance session."""
    
    try:
        # Set up database session service
        verified_db_url = create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            return {
                "success": False,
                "error": "Database configuration error",
                "message": "Could not connect to database"
            }
        
        # Create unique session ID with employee ID embedded
        performance_session_id = f"{session_id}_{employee_id}"
        logger.info(f"Setting up performance evaluation session: {performance_session_id}")
        
        session_service = DatabaseSessionService(db_url=verified_db_url)
        performance_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=performance_session_id
        )
        
        if performance_session:
            logger.info(f"Performance session already exists for ID: {performance_session_id}, reusing it.")
        else:
            performance_session = await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=performance_session_id
            )
            logger.info(f"Performance evaluation session created successfully with app_name: {app_name}")
        
        if not performance_session:
            logger.error(f"Failed to create or retrieve performance session for ID: {performance_session_id}")
            return {
                "success": False,
                "error": "Session creation failed",
                "message": "Could not create performance evaluation session"
            }
        
        logger.info(f"Performance session setup completed successfully for employee: {employee_id}")
        return {
            "success": True,
            "session_service": session_service,
            "performance_session": performance_session,
            "performance_session_id": performance_session_id
        }
        
    except Exception as e:
        logger.error(f"Error setting up performance session for employee {employee_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to set up performance session"
        }


async def _transfer_data_to_session_state(
    performance_session, 
    session_service,
    validated_performance_data: Dict[str, Any],
    company_id: str
) -> EmployeePerformanceData:
    """Transfer validated performance data and company config to session state for agent access."""
    
    try:
        # Parse validated performance data using Pydantic schema
        performance_data = EmployeePerformanceData(**validated_performance_data)
        logger.info(f"Successfully parsed performance data for employee: {performance_data.employee_id}")
        
        # Get company-specific performance evaluation configuration
        config = get_performance_config(company_id)
        logger.info(f"Using performance config for company {config.company_id}.")
        
        # Prepare state delta for performance evaluation data
        # Note: Avoid duplicating the entire validated_performance_data blob in state to keep
        # the event actions payload small. Provide only the pieces that agents actually consume.
        state_delta = {
            # Company-specific configuration for agent access
            "evaluation_config": config.to_dict(),

            # These keys will be accessible in agent instructions using {key_name} syntax
            "employee_info": {
                "employee_id": performance_data.employee_id,
                "employee_name": performance_data.employee_name,
                "evaluation_period": performance_data.evaluation_period.model_dump()
            },
            "attendance_data": [record.model_dump() for record in performance_data.attendance],
            "mood_data": [entry.model_dump() for entry in performance_data.mood],
            "leave_data": [record.model_dump() for record in performance_data.leave],
            "work_logs_data": [entry.model_dump() for entry in performance_data.work_logs],
            "tasks_data": [record.model_dump() for record in performance_data.tasks],
        }

        # Optional: log a rough JSON size estimate for observability (not exact to pickled size)
        try:
            import json as _json
            approx_bytes = len(_json.dumps(state_delta))
            logger.info(f"Performance state_delta approx JSON bytes: {approx_bytes}")
        except Exception:
            pass
        
        # Create event with state delta to transfer data to session
        event = Event(
            invocation_id=f"transfer_performance_data_{performance_data.employee_id}",
            author="system",
            timestamp=time.time(),
            actions=EventActions(state_delta=state_delta)
        )
        
        await session_service.append_event(performance_session, event)
        logger.info(f"Performance data and company config transferred to session state via event for employee: {performance_data.employee_id}")
        
        return performance_data
        
    except Exception as e:
        logger.error(f"Error transferring data to session state for company {company_id}: {e}", exc_info=True)
        # Re-raise the exception as this is a critical failure
        raise