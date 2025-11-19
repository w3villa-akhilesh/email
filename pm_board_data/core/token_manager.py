import time
import json
from app.utils.logger import logger

class TokenManager:
    def __init__(self, token_file="token.json"):
        self.token_file = token_file
        self.token_data = None
        self._load_token()

    def _load_token(self):
        try:
            with open(self.token_file, "r") as file:
                self.token_data = json.load(file)
                logger.info("Loaded token from file.")
        except FileNotFoundError:
            logger.warning("Token file not found, starting with empty token.")

    def save_token(self, token: str, expires_in: int):
        self.token_data = {
            "token": token,
            "expires_at": time.time() + expires_in
        }
        with open(self.token_file, "w") as file:
            json.dump(self.token_data, file)
        logger.info(f"Token saved, expires in {expires_in} seconds.")

    def get_token(self):
        if self.token_data and time.time() < self.token_data.get("expires_at", 0):
            logger.info("Token is valid and loaded.")
            return self.token_data["token"]
        logger.warning("Token expired or not present.")
        return None
