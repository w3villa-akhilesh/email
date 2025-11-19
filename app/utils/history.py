import json
from datetime import datetime
from app.utils.logger import logger

def construct_previous_context(previous_response: str) -> str:
    """
    Constructs the previous context from the given previous_response JSON string or list.

    Args:
        previous_response (str or list): A JSON string or list containing previous queries and responses.

    Returns:
        str: A formatted string in 'role: user/assistant' style.
    """
    previous_context = ""
    previous_response_list = []

    if previous_response:
        if isinstance(previous_response, list):
            previous_response_list = previous_response
        else:
            try:
                previous_response_list = json.loads(previous_response)
                if not isinstance(previous_response_list, list):
                    raise ValueError("previous_response should be a JSON list.")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid previous_response format: {e}")
                previous_response_list = []

    for i, entry in enumerate(previous_response_list, 1):
        if isinstance(entry, dict):
            prev_query = entry.get("query", "").strip()
            prev_resp = entry.get("response", "").strip()
            if prev_query:
                previous_context += f"\nrole: user\ncontent: {prev_query}\n"
            if prev_resp:
                previous_context += f"role: assistant\ncontent: {prev_resp}\n"
        else:
            previous_context += f"\nrole: user\ncontent: [Invalid entry: {entry}]\n"

    return previous_context.strip()
