from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config
from logger import logger

# Create a SQLAlchemy engine
engine = create_engine(config.DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_all_tables():
    """Creates all tables defined in the models."""
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully (if they didn't exist).")

if __name__ == "__main__":
    create_all_tables()