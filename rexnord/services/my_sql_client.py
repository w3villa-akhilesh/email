import mysql.connector
from mysql.connector import Error
from app.utils.logger import logger
import os 
from dotenv import load_dotenv
import json
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.db_models import Base

load_dotenv()

def create_db_url():
    try:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_name = os.getenv("DB_NAME")
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password
        )
        cursor = connection.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME')}")
        logger.info(f"Database {os.getenv('DB_NAME')} created or already exists.")
        connection.commit()

        db_password_encoded = quote_plus(db_password)

        db_url = f"mysql+mysqlconnector://{db_user}:{db_password_encoded}@{db_host}/{db_name}"

        return db_url
    except Error as e:
        logger.error(f"MySQL Error in create_db_if_not: {e}")   


SQLALCHEMY_DATABASE_URL = create_db_url()
# Create engine with resilient pool settings to avoid stale/closed connection errors
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,           # This checks that active connection should be picked.
    pool_recycle=1800,            # recycle connections before MySQL's wait_timeout
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    connect_args={
        # mysql-connector-python uses 'connection_timeout' (seconds)
        "connection_timeout": 20,
    },
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def create_tables_if_not_exist():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

def get_db():
    create_tables_if_not_exist()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_engine():
    return engine
