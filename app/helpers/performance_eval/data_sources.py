from __future__ import annotations

from typing import Optional, Union, Dict, Any
import json
import requests
from requests import exceptions as req_exc

from app.utils.logger import logger
from app.models.schema import EmployeePerformanceData
from app.services.redis_common_state import get_session_data


def get_pms_employee_performance_data(
    session_id: str,
    company_id: str,   # kept for signature parity; unused here
    origin: str,
    employee_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Union[EmployeePerformanceData, Dict[str, str]]:
    """
    Get employee performance data from PMS.

    Returns:
        - EmployeePerformanceData on success
        - {"status": "error", "message": "..."} on any failure
    """
    app_name = "triage_agent"

    # ---- Guard rails
    if not origin:
        logger.error("Missing `origin` for session_id=%s", session_id)
        return {"status": "error", "message": "Origin not provided"}

    origin_norm = origin.strip().rstrip("/")
    url = f"{origin_norm}/api/v1/corps/profiles/performance_data"

    # Load session/token
    try:
        session_data = get_session_data(session_id, app_name) or {}
    except Exception as e:
        logger.exception("Failed to read session data (session_id=%s): %s", session_id, e)
        return {"status": "error", "message": "Could not read session data"}

    token = session_data.get("token")
    if not token:
        logger.error("Missing auth token in session (session_id=%s)", session_id)
        return {"status": "error", "message": "Authorization token missing"}

    headers = {"Authorization": f"Bearer {token}"}
    params: Dict[str, Any] = {"profile_id": employee_id}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    timeout = 15

    def _log_response(prefix: str, resp: requests.Response) -> None:
        body_preview = (resp.text or "")[:500]
        safe_url = getattr(resp.request, "url", url)
        logger.info(
            "%s status=%s url=%s body[:500]=%r",
            prefix, resp.status_code, safe_url, body_preview
        )

    try:
        # ---- Single request
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        logger.info("PMS GET (profile_id) -> %s %s", resp.status_code, getattr(resp.request, "url", url))

        if resp.status_code != 200:
            _log_response("PMS non-200", resp)
            return {"status": "error", "message": f"PMS API error {resp.status_code}"}

        # ---- Parse JSON safely
        try:
            payload_root = resp.json()
        except ValueError:
            body_preview = (resp.text or "")[:2000]
            # logger.error("PMS 200 but non-JSON body. body[:2000]=%r", body_preview)
            return {"status": "error", "message": "PMS returned invalid JSON"}

        # Optional: compact log of the data block
        try:
            # logger.info("PMS 200 JSON %s", json.dumps(payload_root, indent=2, ensure_ascii=False))
            logger.info("PMS data format - JSON ")
        except Exception:
            logger.info("PMS 200 JSON (unserializable preview): %r", str(payload_root)[:2000])

        data_block = payload_root.get("data", {})
        try:
            return EmployeePerformanceData(**data_block)
        except Exception as e:
            logger.exception("Failed to build EmployeePerformanceData: %s; data=%r", e, data_block)
            return {"status": "error", "message": "Invalid PMS data shape"}

    # ---- Network and HTTP-level failures
    except (req_exc.Timeout, req_exc.ConnectTimeout):
        logger.warning("PMS request timed out (url=%s)", url)
        return {"status": "error", "message": "PMS request timed out"}
    except req_exc.ConnectionError as e:
        logger.warning("PMS connection error: %s", e)
        return {"status": "error", "message": "Could not connect to PMS"}
    except req_exc.HTTPError as e:
        logger.warning("PMS HTTP error: %s", e)
        return {"status": "error", "message": "HTTP error talking to PMS"}
    except Exception as e:
        logger.exception("Unexpected error calling PMS: %s", e)
        return {"status": "error", "message": "Failed to fetch performance data"}