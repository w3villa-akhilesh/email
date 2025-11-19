from openai import OpenAI
import os
from dotenv import load_dotenv

# validating balance/expiry of llm key and url.
def validate_completion(api_key: str, base_url: str) -> dict:
    """
    Validates the llm key and base URL by attempting a simple completion request.

    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
        model=os.getenv("KIVO_PM_BOARD_AGENT_MODEL"),
        messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        )
        return True
    except Exception:
        return False
    
# decryption of llm key and urls
def decrypt_hex_string(hex_str: str) -> str:
    try:
        return bytes.fromhex(hex_str).decode('utf-8')
    except Exception:
        raise ValueError("Invalid hex input for decryption")
