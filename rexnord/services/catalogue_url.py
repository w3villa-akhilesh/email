import requests
from typing import Optional
from rexnord.core.constants import (
    REXNORD_INVENTORY_TOKEN,
    REXNORD_INVENTORY_BASE_URL,
    REXNORD_STORE_ID,
)
from app.utils.logger import logger


def _inventory_get(path: str, params: Optional[dict] = None) -> dict:
    url = f"{REXNORD_INVENTORY_BASE_URL}{path}"
    headers = {
        "X-Spree-Token": REXNORD_INVENTORY_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"[inventory GET] {url} params={params}")
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_single_page_catalog_pdf(session_id: str) -> Optional[str]:
    """
    Fetch Single Page Catalogue taxon from the Inventory API and return its PDF URL.

    Returns:
        str | None: Direct PDF URL if found, otherwise None.
    """
    logger.info(f"[get_single_page_catalog_pdf] called | session_id={session_id}")

    endpoint = f"/api/v2/stores/{REXNORD_STORE_ID}/taxons"
    params = {"q": "Single Page Catalogue"}
    try:
        data = _inventory_get(endpoint, params=params)
    except Exception as e:
        logger.exception("[get_single_page_catalog_pdf] API request failed")
        return None

    if not isinstance(data, dict):
        logger.warning("[get_single_page_catalog_pdf] Unexpected response shape")
        return None

    taxons = data.get("taxons") or []
    if not isinstance(taxons, list):
        logger.warning("[get_single_page_catalog_pdf] 'taxons' not a list")
        return None

    # Find exact (case-insensitive) match, else fallback to first
    target = next(
        (t for t in taxons if isinstance(t, dict) and (t.get("name") or "").strip().lower() == "single page catalogue"),
        None,
    ) or (taxons[0] if taxons and isinstance(taxons[0], dict) else None)

    pdf_url = (target or {}).get("pdf_url")
    if not pdf_url:
        logger.info("[get_single_page_catalog_pdf] pdf_url missing in target taxon")
        return None

    return pdf_url
