from typing import Dict, Any
from datetime import datetime
import json
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data
from typing import Dict, Any
from datetime import datetime
import json
from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger
from app.helpers.performance_eval.data_sources  import get_pms_employee_performance_data
from app.helpers.performance_eval.pipelines import _execute_performance_pipeline
from app.helpers.performance_eval.validation_utils import _extract_and_validate_context, _validate_pipeline_prerequisites
from app.helpers.performance_eval.session_handling import _setup_performance_session, _transfer_data_to_session_state
from app.helpers.performance_eval.common_utils import _format_pipeline_response
import os
from datetime import datetime


def _env_int(name: str, default: int) -> int:
    try:
        val = int(os.getenv(name, str(default)))
        return default if val <= 0 else val
    except Exception:
        return default


LIMITS = {
    "attendance": _env_int("PMS_MAX_ATTENDANCE", 100),
    "mood": _env_int("PMS_MAX_MOOD", 100),
    "leave": _env_int("PMS_MAX_LEAVE", 30),
    "work_logs": _env_int("PMS_MAX_WORK_LOGS", 50),
    "tasks": _env_int("PMS_MAX_TASKS", 100),
}

# Sampling strategy: 'recent' (default) or 'stratified'
SAMPLING_STRATEGY = os.getenv("PMS_SAMPLING_STRATEGY", "recent").strip().lower()

def _parse_dt_maybe(val: Any) -> Any:
    # Very lightweight parser for ISO-like strings; falls back to string
    try:
        if isinstance(val, str):
            # Remove Z if present for fromisoformat
            v = val.rstrip("Z")
            return datetime.fromisoformat(v)
        return val
    except Exception:
        return val


def _evenly_spaced_indices(n: int, k: int) -> list[int]:
    if k <= 0 or n <= 0:
        return []
    if k >= n:
        return list(range(n))
    step = (n - 1) / max(k - 1, 1)
    # round to nearest
    return sorted({int(round(i * step)) for i in range(k)})


def _stratified_sample(items: list[dict], max_items: int, key: str | None = None) -> list[dict]:
    if not isinstance(items, list) or max_items is None or max_items <= 0:
        return items
    if len(items) <= max_items:
        return items
    # Sort ascending by key if present, else keep original order
    data = items
    if key and all(isinstance(x, dict) and key in x for x in items):
        try:
            data = sorted(items, key=lambda x: _parse_dt_maybe(x.get(key)))
        except Exception:
            data = items

    n = len(data)
    # Divide into 3 strata: earliest, middle, latest
    third = max(1, n // 3)
    early = data[:third]
    middle = data[third: 2 * third]
    late = data[2 * third:]

    # Ratios from env, default roughly equal thirds
    def _ratios():
        raw = os.getenv("PMS_STRATA_RATIOS", "0.34,0.33,0.33")
        try:
            r = [float(x) for x in raw.split(",")]
            if len(r) != 3:
                return [0.34, 0.33, 0.33]
            s = sum(r)
            return [x / s for x in r] if s > 0 else [0.34, 0.33, 0.33]
        except Exception:
            return [0.34, 0.33, 0.33]

    r1, r2, r3 = _ratios()
    k1 = max(0, int(round(max_items * r1)))
    k2 = max(0, int(round(max_items * r2)))
    k3 = max(0, max_items - k1 - k2)

    def _pick(seg: list[dict], k: int) -> list[dict]:
        idx = _evenly_spaced_indices(len(seg), k)
        return [seg[i] for i in idx]

    sample = _pick(early, k1) + _pick(middle, k2) + _pick(late, k3)
    # Ensure we don't exceed max_items due to rounding
    sample = sample[:max_items]
    return sample


def _trim_list(items: Any, max_items: int, sort_key: str | None = None) -> Any:
    try:
        if not isinstance(items, list):
            return items
        if max_items is None or max_items <= 0:
            return items
        if SAMPLING_STRATEGY == "stratified":
            return _stratified_sample(items, max_items, key=sort_key)
        # Default recent strategy: sort desc by key (if present) and take head
        data = items
        if sort_key and all(isinstance(x, dict) and sort_key in x for x in items):
            try:
                data = sorted(items, key=lambda x: _parse_dt_maybe(x.get(sort_key)), reverse=True)
            except Exception:
                data = items
        return data[:max_items] if len(data) > max_items else data
    except Exception:
        return items


def _compact_performance_data(d: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return d
    before_counts = {k: (len(v) if isinstance(v, list) else None) for k, v in d.items()}
    d["attendance"] = _trim_list(d.get("attendance", []), LIMITS["attendance"], sort_key="date")
    d["mood"] = _trim_list(d.get("mood", []), LIMITS["mood"], sort_key="date")
    # For leave/work_logs, prefer sorting by start date/time when present
    d["leave"] = _trim_list(d.get("leave", []), LIMITS["leave"], sort_key="start")
    d["work_logs"] = _trim_list(d.get("work_logs", []), LIMITS["work_logs"], sort_key="start")
    # Tasks typically don't have timestamps; keep order and slice
    d["tasks"] = _trim_list(d.get("tasks", []), LIMITS["tasks"], sort_key=None)

    after_counts = {k: (len(v) if isinstance(v, list) else None) for k, v in d.items()}
    try:
        reductions = {
            k: {
                "before": before_counts.get(k),
                "after": after_counts.get(k),
                "limit": LIMITS.get(k),
                "strategy": SAMPLING_STRATEGY,
            }
            for k in ["attendance", "mood", "leave", "work_logs", "tasks"]
        }
        logger.info(f"PMS data compaction applied: {json.dumps(reductions)}")
    except Exception:
        pass
    return d


async def set_employee_id_from_name(tool_context: ToolContext, name: str) -> dict:
    """
    Given a name (e.g. 'Aman singh'), search through profile_list in tool context
    and set the corresponding employee_id in the state for further pipeline use.

    Args:
        name (str): The name of the employee entered by the user.
    """
    try:
        raw_profiles = tool_context.state.get("profile_list", {})

        # Handle JSON string
        if isinstance(raw_profiles, str):
            if raw_profiles.strip() == "":
                logger.warning("profile_list is an empty string.")
                return {"success": False, "message": "profile_list is empty. No profiles to match."}
            try:
                raw_profiles = json.loads(raw_profiles)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return {"success": False, "error": "Invalid JSON in profile_list"}

        # Unpack results if it's a dict, or use directly if it's a list
        if isinstance(raw_profiles, dict):
            profiles = raw_profiles.get("results", [])
        elif isinstance(raw_profiles, list):
            profiles = raw_profiles
        else:
            profiles = []

        name_lower = name.strip().lower()

        for emp in profiles:
            if emp.get("name", "").strip().lower() == name_lower:
                tool_context.state["employee_id"] = str(emp["employee_id"])
                return {
                    "success": True,
                    "selected_employee": emp,
                }

        return {
            "success": False,
            "message": f"No match found in profile_list for '{name}'",
        }

    except Exception as e:
        logger.error(f"Error in set_employee_id_from_name: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def inject_performance_data(
    session_id: str, 
    tool_context: ToolContext, 
    employee_id: int, 
    employee_name: str,
    start_date: str, 
    end_date: str
) -> Dict[str, Any]:
    """
    Tool that injects validated employee performance data into session state.
    
    This tool loads employee performance data, validates itand stores it in the tool 
    context state for use by the performance evaluation pipeline.
    
    Args:
        session_id: Unique session identifier for the evaluation process.
        tool_context: ADK tool context for accessing session state
        employee_id: Employee ID for evaluation. Use the `employee_id` from `profile_list`.
        employee_name: Name of the employee for `employee_id` provided .
        start_date: Start date of evaluation period (format: YYYY-MM-DD)
        end_date: End date of evaluation period (format: YYYY-MM-DD)
    
    Note:
        - Donot assume random employee_id, use the employee_id from `suggest_similar_names`.
    
    Returns:
        Success/error status with data summary
    """
    try:

        logger.info(f"Injecting validated performance data for employee: {employee_id} for session: {session_id}")
        # performance_data = get_dummy_employee_performance_data()
        # Get validated data using PMS API or fallback to dummy
        employee_id = str(employee_id)  # Ensure employee_id is a string
        if not employee_id:
            return {
                "success": False,
                "error": "employee_id is required",
                "message": "Please provide a employee_id try again."
            }

        # Extract session data from tool context
        company_id = tool_context.state["company_id"]
        origin = tool_context.state["origin"]
        logger.debug(f"Fetching performance data from origin {origin} with company ID {company_id}")
        performance_data = get_pms_employee_performance_data(session_id, company_id, origin, employee_id, start_date, end_date)

        # Handle error or missing data responses from data source
        if performance_data is None:
            return {
                "success": False,
                "status": "not_found",
                "message": f"Performance data not found for employee {employee_id}",
            }

        # If the data source returned an error dict, surface it as a not_found status
        if isinstance(performance_data, dict):
            status = performance_data.get("status")
            message = performance_data.get("message") or f"Performance data not found for employee {employee_id}"
            if status == "error" or not performance_data:
                return {
                    "success": False,
                    "status": "not_found",
                    "message": message,
                }
            # If a plain dict with data came back, proceed and store it
            performance_data_dict = performance_data
        else:
            # Pydantic model path: update employee_id if needed then dump to dict
            try:
                # Avoid AttributeError for non-models; this block only runs for models
                setattr(performance_data, "employee_id", employee_id)
            except Exception:
                # Ignore if immutable; rely on dump/update below
                pass
            performance_data_dict = performance_data.model_dump()
        
        # Compact large arrays to reduce session state and token usage
        try:
            performance_data_dict = _compact_performance_data(performance_data_dict)
        except Exception as _compact_err:
            logger.warning(f"Compaction skipped due to error: {_compact_err}")

        # Save validated data to tool context state following ADK patterns
        # Using clear key names for session state management
        tool_context.state["validated_performance_data"] = performance_data_dict
        tool_context.state["performance_evaluation_employee_id"] = employee_id
        tool_context.state["performance_evaluation_started"] = datetime.now().isoformat()
        
        # Store session context information for the pipeline execution
        # Note: Session ID creation will be handled in run_performance_evaluation_pipeline
        
        logger.info("Validated performance data successfully injected into session state")
        
        # Pull fields from dict safely for the response
        emp_name = (
            performance_data_dict.get("employee_name")
            if isinstance(performance_data_dict, dict)
            else getattr(performance_data, "employee_name", employee_name)
        )
        evaluation_period = None
        if isinstance(performance_data_dict, dict):
            ep = performance_data_dict.get("evaluation_period") or {}
            start = (ep or {}).get("start_date")
            end = (ep or {}).get("end_date")
            evaluation_period = f"{start} to {end}" if start and end else None
        else:
            try:
                evaluation_period = f"{performance_data.evaluation_period.start_date} to {performance_data.evaluation_period.end_date}"
            except Exception:
                evaluation_period = None

        def _len_safe(container):
            try:
                return len(container) if container is not None else 0
            except Exception:
                return 0

        attendance = performance_data_dict.get("attendance") if isinstance(performance_data_dict, dict) else getattr(performance_data, "attendance", [])
        mood = performance_data_dict.get("mood") if isinstance(performance_data_dict, dict) else getattr(performance_data, "mood", [])
        leave = performance_data_dict.get("leave") if isinstance(performance_data_dict, dict) else getattr(performance_data, "leave", [])
        work_logs = performance_data_dict.get("work_logs") if isinstance(performance_data_dict, dict) else getattr(performance_data, "work_logs", [])
        tasks = performance_data_dict.get("tasks") if isinstance(performance_data_dict, dict) else getattr(performance_data, "tasks", [])

        return {
            "success": True,
            "message": f"Validated performance data loaded for employee {employee_id}",
            "employee_info": {
                "employee_id": employee_id,
                "employee_name": emp_name,
                "evaluation_period": evaluation_period,
            },
            "data_summary": {
                "attendance_records": _len_safe(attendance),
                "mood_entries": _len_safe(mood),
                "leave_records": _len_safe(leave),
                "work_log_entries": _len_safe(work_logs),
                "task_records": _len_safe(tasks),
            },
            "validation_status": "All data validated through Pydantic schema"
        }
        
    except Exception as e:
        logger.error(f"Error injecting performance data: {e}", exc_info=False)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to inject performance data",
            "validation_status": "Data validation failed"
        }

async def run_performance_evaluation_pipeline(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool that orchestrates the sequential performance evaluation pipeline using ADK session service.
    
    This tool creates a SequentialAgent pipeline with 4 sub-agents that process employee
    performance data through metrics calculation, scoring, insight analysis, and report generation.
    Uses DatabaseSessionService for persistent session management following ADK patterns.
    
    Args:
        tool_context: ADK tool context for accessing session state and configuration
        
    Returns:
        Performance evaluation report with pipeline execution details
    """
    try:
        logger.info("Starting performance evaluation pipeline with session service")
        
        # 1. Validate prerequisites
        validation_result = await _validate_pipeline_prerequisites(tool_context)
        if not validation_result["success"]:
            return validation_result
        
        validated_performance_data = validation_result["validated_performance_data"]
        employee_id = validation_result["employee_id"]
        
        # 2. Extract and validate context
        context_result = _extract_and_validate_context(tool_context)
        if not context_result["success"]:
            return context_result
        
        user_id = context_result["user_id"]
        session_id = context_result["session_id"]
        company_id = context_result["company_id"]
        origin = context_result["origin"]
        app_name = context_result["app_name"]
        
        logger.info(f"Running performance evaluation for user: {user_id}, session: {session_id}, employee: {employee_id}, app: {app_name}, origin: {origin}")
        
        # 3. Set up performance session
        session_result = await _setup_performance_session(user_id, session_id, employee_id, app_name)
        if not session_result["success"]:
            return session_result
        
        session_service = session_result["session_service"]
        performance_session = session_result["performance_session"]
        performance_session_id = session_result["performance_session_id"]
        
        # 4. Transfer data to session state
        performance_data = await _transfer_data_to_session_state(performance_session, session_service, validated_performance_data, company_id)
        
        # 5. Execute performance pipeline
        pipeline_result = await _execute_performance_pipeline(
            session_service, performance_session_id, user_id, app_name, company_id, origin, employee_id
        )
        if not pipeline_result["success"]:
            return pipeline_result

        review_insight_data = get_session_data(performance_session_id, app_name)

        review_insight_reasoning = review_insight_data.get('insight_analysis_agent_analysis')

        # print("review_insight_reasoning:",review_insight_reasoning)


        # 6. Format and return response
        return _format_pipeline_response(
            performance_data,
            user_id,
            performance_session_id,
            app_name,
            pipeline_result["final_response"],
            pipeline_result["first_message_event_id"],
            pipeline_result["performance_pipeline"],
            pipeline_result["sub_agents"],
            review_insight_reasoning
        )
        
    except Exception as e:
        logger.error(f"Error in performance evaluation pipeline: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to run performance evaluation pipeline"
        }