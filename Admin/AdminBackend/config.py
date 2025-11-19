import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for Admin Backend"""
    
    # Database Configuration
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    
    DATABASE_URL = (
        f"mysql+mysqlconnector://{DB_USER}:"
        f"{DB_PASSWORD}@{DB_HOST}/"
        f"{DB_NAME}"
    )
    
    # Kivo OAuth Configuration
    KIVO_CLIENT_ID = os.getenv("KIVO_CLIENT_ID")
    KIVO_CLIENT_SECRET = os.getenv("KIVO_CLIENT_SECRET")
    KIVO_PROVIDER_URL = os.getenv("KIVO_PROVIDER_URL")
    KIVO_CALLBACK_URL = os.getenv("KIVO_CALLBACK_URL")
    KIVO_SCOPE = os.getenv("KIVO_SCOPE")
    KIVO_AUTHORIZE_PATH = os.getenv("KIVO_AUTHORIZE_PATH")
    
    # Admin Dashboard Configuration
    ADMIN_DASHBOARD_URL = os.getenv("ADMIN_DASHBOARD_URL", "https://admin-agents.kivo.ai")
    
    # Authentication
    AUTH_TOKEN = os.getenv("AUTH_TOKEN")
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "https://admin-agents.kivo.ai,http://localhost:3000,http://localhost:4200,https://demo-admin-agents.kivo.ai,https://demo-admin-agents.kivo.ai/adk_web_info,https://admin-agents.kivo.ai/adk_web_info"
    )
    # Parse the comma-separated origins string into a list
    ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    
    # App Configuration
    APP_HOST = "0.0.0.0"
    APP_PORT = 8000
    DEBUG = True

# Create a global config instance
config = Config()
