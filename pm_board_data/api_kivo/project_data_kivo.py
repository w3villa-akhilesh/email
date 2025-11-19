import requests
from app.utils.logger import logger
from pm_board_data.core.config import PROJECT_DATA_URL

def fetch_project_data():
    logger.info("Fetching project data using the provided token.")
    try:
        response = requests.get(PROJECT_DATA_URL)
        if response.status_code == 200:
            logger.info(f"Successfully fetched project data {response}.")
            return response.json()
        else:
            logger.error(f"Failed to fetch project data: {response.status_code} - {response.text}")
            raise Exception("Failed to fetch project data")
    except Exception as e:
        logger.error(f"Error while fetching project data: {str(e)}")
        raise