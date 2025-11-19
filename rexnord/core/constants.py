import os
from dotenv import load_dotenv

load_dotenv()
REXNORD_MCP_SERVER_URL = "http://0.0.0.0:9016/sse"

# Rexnord Inventory API auth token
REXNORD_INVENTORY_TOKEN = os.getenv("REXNORD_INVENTORY_TOKEN")
if not REXNORD_INVENTORY_TOKEN:
    raise ValueError(
        "REXNORD_INVENTORY_TOKEN environment variable is not set. Please set it in your .env file."
    )

# Rexnord Inventory API base URL (e.g., https://inventory.rexnord.com/api)
REXNORD_INVENTORY_BASE_URL = os.getenv("REXNORD_INVENTORY_BASE_URL")
if not REXNORD_INVENTORY_BASE_URL:
    raise ValueError(
        "REXNORD_INVENTORY_BASE_URL environment variable is not set. Please set it in your .env file."
    )

# Normalize by removing trailing slash
REXNORD_INVENTORY_BASE_URL = REXNORD_INVENTORY_BASE_URL.rstrip("/")

# Rexnord Store ID
REXNORD_STORE_ID = os.getenv("REXNORD_STORE_ID")
if not REXNORD_STORE_ID:
    raise ValueError(
        "REXNORD_STORE_ID environment variable is not set. Please set it in your .env file."
    )
REXNORD_STORE_ID = REXNORD_STORE_ID.strip()