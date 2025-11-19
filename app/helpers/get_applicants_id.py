from typing import List
from app.utils.logger import logger
from app.helpers.elastic_search import get_es_client
from dotenv import load_dotenv
import os

load_dotenv()

async def fetch_all_applicant_ids() -> List[int]:
    """
    Fetches all job applicant IDs from Elasticsearch.

    Returns:
        List[int]: List of applicant IDs.
    """
    COMPANY_ID = os.getenv('COMPANY_ID', "1")

    index_name = f"job_applicants_{COMPANY_ID}"
    es = get_es_client()

    try:
        # Step 1: Get total count of applicants
        count_query = {
            "query": {
                "match_all": {}
            },
            "size": 1
        }

        logger.debug("Fetching total number of applicants...")
        count_response = es.search(index=index_name, body=count_query)
        total_hits = count_response["hits"]["total"]["value"]

        logger.info(f"Total applicants found: {total_hits}")

        # Step 2: Fetch all applicants with that total size
        full_fetch_query = {
            "query": {
                "match_all": {}
            },
            "size": total_hits
        }

        logger.debug("Fetching all applicant documents...")
        full_response = es.search(index=index_name, body=full_fetch_query)
        hits = full_response["hits"]["hits"]

        applicant_ids = []
        for hit in hits:
            applicant = hit.get("_source", {})
            applicant_id = applicant.get("id")
            if applicant_id is not None:
                applicant_ids.append(applicant_id)

        logger.info(f"Fetched {len(applicant_ids)} applicant IDs.")
        return applicant_ids

    except Exception as e:
        logger.error(f"Failed to fetch applicants: {str(e)}")
        return []
