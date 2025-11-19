import json
from typing import Optional, List
from app.utils.logger import logger
try:
    from google.adk.tools.tool_context import ToolContext
except Exception:
    # Fallback shim for type hints if ToolContext isn't available in some contexts
    class ToolContext:  # type: ignore
        state: dict
        def __init__(self):
            self.state = {}

from app.services.redis_common_state import (
        save_session_data,
        get_session_data,
        ttl as DEFAULT_TTL,
        redis_client,
    )


FIELD_NAME = "imgs"  # field inside the session hash
# Global TTL override for image list storage (2 days)
IMAGE_LIST_TTL_SECONDS = 60 * 60 * 24 * 2  # 172800


def _normalize_index(length: int, index: int) -> Optional[int]:
    """Normalize possibly-negative index to [0, length-1]; return None if OOR."""
    if length <= 0:
        return None
    if index < 0:
        index = length + index
    if index < 0 or index >= length:
        return None
    return index


def _get_list(session_id: str, app_name: Optional[str]) -> List[str]:
    """Fetch the image list (as Python list of URLs) from the session hash."""
    try:
        data = get_session_data(session_id, app_name)
        raw = data.get(FIELD_NAME)
        if not raw:
            return []
        try:
            lst = json.loads(raw)
            return lst if isinstance(lst, list) else []
        except json.JSONDecodeError:
            return []
    except Exception as e:
        logger.error(f"_get_list error for session={session_id}, app={app_name}: {e}", exc_info=True)
        return []


def _set_list(session_id: str, app_name: Optional[str], items: List[str], ttl_override: Optional[int] = None) -> None:
    """Persist the image list back to the session hash and refresh TTL."""
    try:
        save_session_data(session_id, {FIELD_NAME: json.dumps(items)}, app_name)
        # Apply a TTL override on the session hash when image list is updated
        try:
            effective_ttl = ttl_override if ttl_override is not None else IMAGE_LIST_TTL_SECONDS
            if effective_ttl:
                key = f"session:{session_id}"
                if app_name:
                    key = f"session:{session_id}:{app_name}"
                redis_client.expire(key, int(effective_ttl))
                logger.debug(f"[_set_list] Applied TTL={int(effective_ttl)}s on key='{key}' for FIELD_NAME='{FIELD_NAME}' (count={len(items)})")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"_set_list error for session={session_id}, app={app_name}: {e}", exc_info=True)
        raise


def push_image_s3_url(
    session_id: str,
    app_name: Optional[str],
    s3_url: str,
    max_items: int = 4,
    ttl_override: Optional[int] = IMAGE_LIST_TTL_SECONDS,
) -> int:
    """
    Append one S3 URL to the list field in the session hash; keep only last `max_items`.
    Returns the new list length.
    """
    try:
        logger.debug(f"[push_image_s3_url] session_id={session_id}, app_name={app_name}, url={s3_url}, max_items={max_items}, ttl_override={ttl_override}")
        items = _get_list(session_id, app_name)
        prev_len = len(items)
        items.append(s3_url)
        removed = 0
        if len(items) > max_items:
            removed = len(items) - max_items
            items = items[-max_items:]
        _set_list(session_id, app_name, items, ttl_override)
        new_len = len(items)
        new_index = new_len - 1 if new_len > 0 else 0
        if removed:
            logger.debug(f"[push_image_s3_url] trimmed list to last {max_items} items (removed={removed})")
        logger.info(f"[push_image_s3_url] added image url (index={new_index}) for session={session_id}, app={app_name}; size {prev_len} -> {new_len}")
        return new_len
    except Exception as e:
        logger.error(f"[push_image_s3_url] error: {e}", exc_info=True)
        raise


def get_image_s3_url(session_id: str, app_name: Optional[str], index: int) -> Optional[str]:
    """
    Get the S3 URL at zero-based index from the list field. Supports negative index.
    Returns None if out of range.
    """
    try:
        items = _get_list(session_id, app_name)
        idx = _normalize_index(len(items), index)
        return items[idx] if idx is not None else None
    except Exception as e:
        logger.error(f"get_image_s3_url error: {e}", exc_info=True)
        return None


def remove_image_by_index(
    session_id: str,
    app_name: Optional[str],
    index: int,
    ttl_override: Optional[int] = None,
) -> bool:
    """Remove a single item by index from the list field. Returns True if removed."""
    try:
        items = _get_list(session_id, app_name)
        idx = _normalize_index(len(items), index)
        if idx is None:
            return False
        items.pop(idx)
        _set_list(session_id, app_name, items, ttl_override)
        logger.info(f"remove_image_by_index: session={session_id}, app={app_name}, index={index}")
        return True
    except Exception as e:
        logger.error(f"remove_image_by_index error: {e}", exc_info=True)
        return False


def list_image_s3_urls(session_id: str, app_name: Optional[str]) -> List[str]:
    """Return all S3 URLs in order (oldest → newest within kept window) from the hash field."""
    return _get_list(session_id, app_name)


def clear_image_list(session_id: str, app_name: Optional[str]) -> bool:
    """Clear the list field by setting it to an empty list."""
    try:
        _set_list(session_id, app_name, [])
        logger.info(f"clear_image_list: session={session_id}, app={app_name}")
        return True
    except Exception:
        return False


# ==== LLM Tool: pick image URL by numeric index ====

async def pick_image_url_by_index(
    index: Optional[int] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Pick a stored S3 image URL by numeric index.
    
    Args:
      index: Optional zero-based positive index (0..5). If not provided, defaults to 0 (the first image).
    Returns:
      { "status": "success", "index": <int>, "url": <str> }
      or { "status": "error", "message": <str>, "count": <int> }
    """
    try:
        logger.debug(f"[pick_image_url_by_index] called with index={index}, has_tool_context={bool(tool_context)}")

        if not tool_context or not hasattr(tool_context, "state"):
            logger.warning("[pick_image_url_by_index] Missing tool_context or state")
            return {"status": "error", "message": "Missing tool_context"}

        state = tool_context.state
        session_id = state.get("session_id")
        app_name = state.get("app_name")
        logger.debug(f"[pick_image_url_by_index] session_id={session_id}, app_name={app_name}")
        if not session_id:
            logger.warning("[pick_image_url_by_index] session_id not found in tool_context.state")
            return {"status": "error", "message": "Missing session_id in tool_context.state"}

        images = list_image_s3_urls(session_id, app_name)
        count = len(images)
        logger.debug(f"[pick_image_url_by_index] fetched {count} image URL(s) from Redis")
        if count == 0:
            return {"status": "error", "message": "No images stored for this session", "count": 0}

        # Determine index: default to 0 (first image). Only allow non-negative indices in range.
        if index is None:
            idx = 0
            logger.debug("[pick_image_url_by_index] index not provided; defaulting to 0 (first image)")
        else:
            if not isinstance(index, int):
                logger.warning(f"[pick_image_url_by_index] Non-integer index provided: {index}")
                idx = None
            elif index < 0 or index >= count:
                logger.warning(f"[pick_image_url_by_index] Out-of-range index provided: {index}; count={count}")
                idx = None
            else:
                idx = index
                logger.debug(f"[pick_image_url_by_index] using provided index={idx}")

        if idx is None:
            return {
                "status": "error",
                "message": f"Invalid index {index}. Valid range: 0..{max(0, count-1)}",
                "count": count,
            }

        url = images[idx]
        logger.debug(f"[pick_image_url_by_index] selected idx={idx}, url={url}")

        try:
            tool_context.state["selected_image_url"] = url
            tool_context.state["selected_image_index"] = idx
            logger.debug("[pick_image_url_by_index] wrote selected_image_url and selected_image_index to tool_context.state")
        except Exception as se:
            logger.debug(f"[pick_image_url_by_index] unable to write to tool_context.state: {se}")

        return {"status": "success", "index": idx, "url": url}
    except Exception as e:
        logger.error(f"[pick_image_url_by_index] error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
