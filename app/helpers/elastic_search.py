import os
from elasticsearch import Elasticsearch
import urllib3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OPTIONAL: Disable SSL warnings (use only for local testing or self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Configuration from environment variables ===
ELASTIC_HOST = os.getenv("ELASTIC_HOST")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
VERIFY_CERTS = False

# === Connect to Elasticsearch ===
def get_es_client():
    es = Elasticsearch(
        ELASTIC_HOST,
        basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
        verify_certs=VERIFY_CERTS
    )
    if not es.ping():
        raise ConnectionError("Failed to connect to Elasticsearch")
    return es 