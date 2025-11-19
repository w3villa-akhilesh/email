from typing import Dict, Any
import json
from app.utils.logger import logger
from app.models.schema import EmployeePerformanceData
from google.adk.agents.callback_context import CallbackContext
from app.services.redis_common_state import save_session_data

def _format_pipeline_response(
    performance_data: EmployeePerformanceData,
    user_id: str,
    performance_session_id: str,
    app_name: str,
    final_response: str,
    first_message_event_id: str,
    performance_pipeline,
    sub_agents: list,
    review_insight_reasoning: dict

) -> Dict[str, Any]:
    """Format the final pipeline response."""
    
    try:
        logger.info(f"Formatting pipeline response for employee: {performance_data.employee_id}")


        response = {
            "success": True,
            "message": "Performance evaluation completed successfully",
            # "employee_id": performance_data.employee_id,
            "employee_name": performance_data.employee_name,
            # "user_id": user_id,
            # "session_id": performance_session_id,
            # "app_name": app_name,
            "evaluation_report": final_response,
            # "event_id": first_message_event_id,
            # "pipeline_info": {
            #     "name": performance_pipeline.name,
            #     "sub_agents": [agent.name for agent in sub_agents],
            #     "agent_count": len(sub_agents),
            #     "execution_status": "completed",
            #     "session_format": "session_id_employee_id"
            # },
            "reasoning_data_for_analysis": review_insight_reasoning

        }
    
        
        logger.info(f"Pipeline response formatted successfully for employee: {performance_data.employee_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error formatting pipeline response for employee {performance_data.employee_id}: {e}", exc_info=True)
        # Return a basic error response
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to format pipeline response",
            "employee_id": getattr(performance_data, 'employee_id', 'unknown'),
            "employee_name": getattr(performance_data, 'employee_name', 'unknown')
        }


async def save_insight_analysis(callback_context: CallbackContext, performance_session_id, app_name):
    insight_analysis_agent_analysis = callback_context.state.to_dict()

    # ---- pick values (safe defaults)
    validated_performance_data = insight_analysis_agent_analysis.get("validated_performance_data", {}) or {}

    attendance_data = validated_performance_data.get("attendance")
    leave = validated_performance_data.get("leave")
    work_logs = validated_performance_data.get("work_logs")
    insights_and_trends = validated_performance_data.get("insights_and_trends")

    performance_scores = insight_analysis_agent_analysis.get("performance_scores")
    confidence_level = (performance_scores or {}).get("confidence_level")
    data_quality_notes = (performance_scores or {}).get("data_quality_notes")

    evaluation_config = insight_analysis_agent_analysis.get("evaluation_config")

    # ---- build picked payload
    picked_payload = {
        "attendance_data": attendance_data,
        "leave": leave,
        "work_logs": work_logs,
        "insights_and_trends": insights_and_trends,
        "performance_scores": performance_scores,
        "confidence_level": confidence_level,
        "data_quality_notes": data_quality_notes,
        "evaluation_config": evaluation_config,
    }

    # Serialize picked values only
    payload_str = json.dumps(picked_payload, indent=1, default=str)

    logger.debug(f"insight_analysis_agent_analysis (picked): {payload_str}")

    # store the picked payload in redis
    save_session_data(
        performance_session_id,
        {"insight_analysis_agent_analysis": payload_str},
        app_name,
    )