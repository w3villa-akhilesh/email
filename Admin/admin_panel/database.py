"""
Database configuration and connection management for Admin Panel
"""
import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(self):
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD') 
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = os.getenv('DB_PORT', '3306')
        self.db_name = os.getenv('DB_NAME')
        
        # Validate required environment variables
        if not all([self.db_user, self.db_password, self.db_name]):
            raise ValueError("Missing required database environment variables: DB_USER, DB_PASSWORD, DB_NAME")
    
    @property
    def database_url(self) -> str:
        """Generate database URL"""
        return (
            f"mysql+mysqlconnector://{self.db_user}:"
            f"{self.db_password}@{self.db_host}:{self.db_port}/"
            f"{self.db_name}"
        )

# Initialize database configuration
db_config = DatabaseConfig()

# Create engine with connection pooling and optimizations
engine = create_engine(
    db_config.database_url,
    echo=False,  # Set to True for SQL debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    """
    Dependency function to get database session.
    Use this in FastAPI endpoints with Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database health check
def check_database_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()  # Fetch the result
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

# Create all tables
def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False

# Database metadata for SQLAdmin
metadata = MetaData()
metadata.bind = engine

if __name__ == "__main__":
    # Test database connection and create tables
    print("Testing database connection...")
    if check_database_connection():
        print("Creating tables...")
        create_tables()
    else:
        print("Database connection failed!")
