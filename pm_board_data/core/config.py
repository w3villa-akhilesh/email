from dotenv import load_dotenv
import os
from app.utils.logger import logger


load_dotenv()  # Load environment variables from .env

BASE_URL = os.getenv('BASE_URL')
# Load Kivo API base URL from .env
KIVO_API_BASE_URL = os.getenv('KIVO_API_BASE_URL')

if not KIVO_API_BASE_URL:
    logger.error("KIVO_API_BASE_URL not set in .env file!")
else:
    logger.info("Kivo API Base URL loaded from .env")


# Load Kivo token from .env
KIVO_AGENT_TOKEN = os.getenv("KIVO_AUTH_TOKEN")

if not KIVO_AGENT_TOKEN:
    logger.error("KIVO_AGENT_TOKEN not set in .env file!")


# Load project_id
PROJECT_ID=os.getenv("COMPANY_ID")

if not PROJECT_ID:
    logger.error("Project_id not set in .env file!")

# Load Kivo PROJECT API URL from .env
PROJECT_DATA_URL = f"{KIVO_API_BASE_URL}/api/v1/companies/{PROJECT_ID}/projects_overview?pm_board_access_token={KIVO_AGENT_TOKEN}"

logger.info("Configuration loaded from .env file")