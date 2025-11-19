from pm_board_data.core.token_manager import TokenManager
from pm_board_data.api_kivo.sign_in_kivo import sign_in
from pm_board_data.api_kivo.project_data_kivo import fetch_project_data
from app.utils.logger import logger
import os 

# token_manager = TokenManager()

def get_project_data():
    logger.info("Checking if a valid token exists before fetching project data.")
    
    token = os.getenv("KIVO_AUTH_TOKEN")

    if not token:
        logger.info("Token expired or not present. Check you env")
        # token = sign_in()
        # token_manager.save_token(token, expires_in=86400)  # Token valid for 24 hours

    logger.info("Fetching project data using valid token.")
    # Fetch project data using the token
    project_data = fetch_project_data(token)
    return project_data
