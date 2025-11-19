"""
SQLAlchemy models for Admin Panel
These models match the actual database schema
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, BIGINT, BLOB, TIMESTAMP
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

class User(Base):
    """User model for admin panel"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    kivo_id = Column(String(255), unique=True, index=True, nullable=False)
    firstName = Column(String(255))
    dp_url_small = Column(String(255))
    email = Column(String(255), unique=True)
    timeZone = Column(String(255))
    refresh_token = Column(String(255))
    access_token = Column(String(255))

    def __repr__(self):
        return f"<User(kivo_id='{self.kivo_id}', firstName='{self.firstName}')>"

    def __str__(self):
        return f"{self.firstName} ({self.email})"

class Event(Base):
    """Event model for admin panel - matches actual database schema"""
    __tablename__ = "events"

    id = Column(String(128), primary_key=True, index=True)
    app_name = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    session_id = Column(String(128), nullable=False)
    invocation_id = Column(String(256), nullable=False)
    author = Column(String(256), nullable=False)
    branch = Column(String(256))
    timestamp = Column(DateTime, nullable=False)
    content = Column(Text)  # LONGTEXT in MySQL
    actions = Column(BLOB, nullable=False)
    long_running_tool_ids_json = Column(Text)
    grounding_metadata = Column(Text)  # LONGTEXT in MySQL
    partial = Column(Boolean)  # TINYINT in MySQL
    turn_complete = Column(Boolean)  # TINYINT in MySQL
    error_code = Column(String(256))
    error_message = Column(String(1024))
    interrupted = Column(Boolean)  # TINYINT in MySQL

    def __repr__(self):
        return f"<Event(id={self.id}, app_name='{self.app_name}', session_id='{self.session_id}')>"

    def __str__(self):
        return f"{self.app_name} - {self.session_id}"


class LLMCredentials(Base):
    """LLM Credentials model - matches actual database schema"""
    __tablename__ = "llm_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String(100), nullable=False, index=True)
    llm_model = Column(String(100), nullable=False) 
    llm_key = Column(String(512), nullable=False)
    llm_base_url = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=False)
    origin = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<LLMCredentials(id={self.id}, company_id='{self.company_id}', app_name='{self.app_name}')>"

    def __str__(self):
        return f"{self.company_id} - {self.app_name} ({self.llm_model})"

class SessionMode(Base):
    """Session Mode model for admin panel"""
    __tablename__ = "session_modes" 

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    mode = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<SessionMode(id={self.id}, session_id='{self.session_id}', mode='{self.mode}')>"

    def __str__(self):
        return f"{self.session_id} - {self.mode}"

class ChatAttachment(Base):
    """Chat Attachments model"""
    __tablename__ = "chat_attachments"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(String(255), nullable=False)
    message_id = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    s3_url = Column(Text, nullable=False)
    file_name = Column(String(500))
    file_type = Column(String(100))
    file_size = Column(BIGINT)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __str__(self):
        return f"{self.file_name} - {self.user_id}"

class CompanyIntegrationConfig(Base):
    """Company Integration Configuration model"""
    __tablename__ = "company_integration_config"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(100), nullable=False)
    resume_parser_api_url = Column(String(255), nullable=False)
    resume_parser_access_token = Column(String(255), nullable=False)
    kivo_resume_api_url = Column(String(255))
    ats_api_base_url = Column(String(255))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __str__(self):
        return f"Company {self.company_id} - Integration Config"

class EmailInboxConfig(Base):
    """Email Inbox Configuration model"""
    __tablename__ = "email_inbox_config"

    id = Column(Integer, primary_key=True, index=True)
    account_email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    imap_server = Column(String(255), nullable=False)
    imap_port = Column(Integer, nullable=False)
    company_id = Column(String(100), nullable=False)
    domain = Column(String(255))
    resume_parser_access_token = Column(String(255))
    llm_key = Column(String(512))
    llm_base_url = Column(String(255))
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __str__(self):
        return f"{self.account_email} - {self.company_id}"

class IATSUserSession(Base):
    """IATS User Sessions model"""
    __tablename__ = "iats_user_sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False)
    mode = Column(String(50))
    created_at = Column(DateTime)
    last_summary = Column(Text)
    is_renamed = Column(Boolean, nullable=False)
    app_name = Column(String(255))

    def __str__(self):
        return f"Session {self.session_id} - {self.user_id}"

class IATSLLMCredentials(Base):
    """IATS LLM Credentials model"""
    __tablename__ = "iats_llm_credentials"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(100), nullable=False)
    llm_model = Column(String(100), nullable=False)
    llm_key = Column(String(512), nullable=False)
    llm_base_url = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=False)
    origin = Column(String(100), nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __str__(self):
        return f"IATS - {self.company_id} - {self.app_name}"

class Session(Base):
    """Sessions model"""
    __tablename__ = "sessions"

    id = Column(String(128), primary_key=True, index=True)
    app_name = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    state = Column(Text, nullable=False)  # LONGTEXT
    create_time = Column(DateTime, nullable=False)
    update_time = Column(DateTime, nullable=False)

    def __str__(self):
        return f"{self.app_name} - {self.user_id} - {self.id}"
