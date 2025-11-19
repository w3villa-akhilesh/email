import requests
from pm_board_data.core.config import KIVO_API_BASE_URL
from app.utils.logger import logger
from pm_board_data.core.config import EMAIL, PASSWORD

SIGN_IN_URL = f"{KIVO_API_BASE_URL}/api/v1/users/sign_in"

HEADERS = {
    'Content-Type': 'application/json',
}
def sign_in():
    logger.info("Attempting to sign in using provided credentials.")
    try:
        response = requests.post(SIGN_IN_URL, headers=HEADERS, json={
            "email": EMAIL,
            "password": PASSWORD
        })
        print("response",response)
        if response.status_code== 200:
            data = response.json()
            token = data["authorization"]["token"]
            logger.info(f"token: {token}")
            return token
        else:
            logger.error(f"Sign-in failed with status code {response.status_code}: {response.text}")
            raise Exception("Sign-in failed")
    except Exception as e:
        logger.error(f"Error during sign-in: {str(e)}")
        raise