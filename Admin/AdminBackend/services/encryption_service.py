from cryptography.fernet import Fernet
from typing import Optional
import os
from dotenv import load_dotenv
from logger import logger

# Load environment variables
load_dotenv()

def get_fernet_key() -> str:
    """
    Get the Fernet encryption key from environment variables.
    
    Returns:
        str: The Fernet key from environment variables
        
    Raises:
        ValueError: If FERNET_KEY is not set in environment variables
    """
    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        logger.error("FERNET_KEY not found in environment variables")
        raise ValueError("FERNET_KEY must be set in environment variables")
    return fernet_key

def encrypt_api_key(plaintext: str) -> str:
    """
    Encrypt an API key using Fernet encryption.
    
    Args:
        plaintext (str): The plain text API key to encrypt
        
    Returns:
        str: The encrypted API key
        
    Raises:
        Exception: If encryption fails
    """
    try:
        fernet_key = get_fernet_key()
        fernet = Fernet(fernet_key.encode())
        encrypted = fernet.encrypt(plaintext.encode()).decode()
        logger.info("API key encrypted successfully")
        return encrypted
    except ValueError as e:
        logger.error(f"Fernet key configuration error: {str(e)}")
        raise Exception(f"Failed to encrypt API key: {str(e)}")
    except Exception as e:
        logger.error(f"Error encrypting API key: {str(e)}")
        raise Exception(f"Failed to encrypt API key: {str(e)}")