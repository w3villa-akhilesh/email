import os
from elasticsearch import Elasticsearch
import urllib3
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# OPTIONAL: Disable SSL warnings (use only for local testing or self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Configuration from environment variables ===
ELASTIC_HOST = os.getenv("ELASTIC_HOST")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
VERIFY_CERTS = os.getenv("VERIFY_CERTS")

logger = logging.getLogger(__name__)

# === Connect to Elasticsearch ===
def get_es_client():
    """
    Get Elasticsearch client with improved error handling and resilience.
    
    Returns:
        Elasticsearch: The ES client if connection is successful
        
    Raises:
        ConnectionError: If connection fails after validating configuration
    """
    # Validate configuration
    if not ELASTIC_HOST:
        logger.error("ELASTIC_HOST environment variable not set")
        raise ConnectionError("Elasticsearch configuration error: ELASTIC_HOST not configured")
    
    if not ELASTIC_USERNAME or not ELASTIC_PASSWORD:
        logger.error("Elasticsearch credentials not properly configured")
        raise ConnectionError("Elasticsearch configuration error: credentials not configured")
    
    try:
        es = Elasticsearch(
            [ELASTIC_HOST],  # ES 7.x expects a list of hosts
            http_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
            verify_certs=VERIFY_CERTS,
            timeout=30,
            retry_on_timeout=True,
            max_retries=3
        )
        
        # Test connection with error handling
        if not es.ping():
            logger.error(f"Failed to ping Elasticsearch at {ELASTIC_HOST}")
            raise ConnectionError(f"Cannot reach Elasticsearch server at {ELASTIC_HOST}")
            
        logger.debug(f"Successfully connected to Elasticsearch at {ELASTIC_HOST}")
        return es
        
    except Exception as e:
        logger.error(f"Elasticsearch connection error: {str(e)}")
        if "ConnectionError" in str(type(e)):
            raise ConnectionError(f"Failed to connect to Elasticsearch: {str(e)}")
        else:
            raise ConnectionError(f"Elasticsearch client error: {str(e)}")