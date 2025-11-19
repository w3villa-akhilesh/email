"""
Configuration settings for Admin Panel
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Settings:
    """Application settings class"""
    
    # Database Configuration
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "")
    
    # Admin Authentication
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    
    # Optional OAuth Integration
    KIVO_CLIENT_ID: Optional[str] = os.getenv("KIVO_CLIENT_ID")
    KIVO_CLIENT_SECRET: Optional[str] = os.getenv("KIVO_CLIENT_SECRET")
    KIVO_PROVIDER_URL: Optional[str] = os.getenv("KIVO_PROVIDER_URL")
    
    @property
    def database_url(self) -> str:
        """Generate database URL"""
        return (
            f"mysql+mysqlconnector://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are present"""
        required_settings = [
            ("DB_USER", self.DB_USER),
            ("DB_PASSWORD", self.DB_PASSWORD),
            ("DB_NAME", self.DB_NAME),
        ]
        
        missing_settings = [name for name, value in required_settings if not value]
        
        if missing_settings:
            print(f"❌ Missing required environment variables: {', '.join(missing_settings)}")
            print("Please set these variables in your .env file or environment")
            return False
        
        return True

# Create global settings instance
settings = Settings()

# Environment configuration examples
ENV_EXAMPLE = """
# Copy this to .env file and update with your values

# Database Configuration
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database_name

# Admin Panel Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SECRET_KEY=your-super-secret-key-for-session-management

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8001

# Optional: OAuth Integration
KIVO_CLIENT_ID=your_kivo_client_id
KIVO_CLIENT_SECRET=your_kivo_client_secret
KIVO_PROVIDER_URL=https://your-kivo-provider.com
"""

if __name__ == "__main__":
    print("🔧 Admin Panel Configuration")
    print("=" * 40)
    
    if settings.validate_required_settings():
        print("✅ All required settings are configured")
        print(f"📊 Database: {settings.DB_NAME} on {settings.DB_HOST}:{settings.DB_PORT}")
        print(f"🔐 Admin User: {settings.ADMIN_USERNAME}")
        print(f"🌐 Server: {settings.HOST}:{settings.PORT}")
    else:
        print("\n📝 Example .env file configuration:")
        print(ENV_EXAMPLE)
