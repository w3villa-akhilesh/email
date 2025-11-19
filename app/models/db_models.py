from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, JSON, func, BigInteger, Index, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.dialects.mysql import VARCHAR

Base = declarative_base()

class User(Base):
    """User model matching the existing user table structure"""
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

class UserSession(Base):
    __tablename__ = "iats_user_sessions"

    session_id = Column(String(255), primary_key=True)  # uniquely identifies a session
    user_id = Column(String(255), nullable=False, index=True)  # multiple sessions per user
    mode = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_summary = Column(Text, nullable=True, default="Temporary chat")
    is_renamed = Column(Boolean, nullable=False, default=False)
    app_name = Column(String(255), nullable=True)
    history = relationship("SessionHistory", back_populates="session", uselist=False)

class SessionHistory(Base):
    __tablename__ = "iats_session_histories"

    session_id = Column(String(255), ForeignKey("iats_user_sessions.session_id"), primary_key=True)
    history = Column(Text, nullable=False)

    session = relationship("UserSession", back_populates="history")
# indexing searching 


class CustomMatchingCriteria(Base):
    __tablename__ = "custom_matching_criteria"

    custom_matching_id = Column(String(100), primary_key=True, autoincrement=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    matching_criteria = Column(MySQLJSON, nullable=False)
    scoring_criteria = Column(MySQLJSON, nullable=True)
    matching_status = Column(String(50), default="in_progress", nullable=False, index=True)
    job_applicant_ids = Column(MySQLJSON, nullable=False)


class CustomMatchingResultsApplicantData(Base):
    __tablename__ = "custom_matching_results_applicant_data"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    custom_matching_id = Column(String(100), ForeignKey("custom_matching_criteria.custom_matching_id"), nullable=False, index=True)
    applicant_id = Column(String(255), nullable=False, index=True)
    matching_score = Column(String(10), nullable=True)
    matching_score_reasoning = Column(String(255), nullable=True)

class MatchingNotification(Base):
    __tablename__ = "matching_notifications"

    id = Column(Integer, primary_key=True, index=True)
    custom_matching_id = Column(String(100), ForeignKey("custom_matching_criteria.custom_matching_id"), nullable=False, index=True)
    session_id = Column(String(255), ForeignKey("iats_user_sessions.session_id"), nullable=False, index=True)
    session = relationship("UserSession", backref="notifications")
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    is_clear = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LLMCredentials(Base):
    __tablename__ = "llm_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)  # 'openai', 'anthropic', etc.
    base_url = Column(String(255), nullable=False)
    api_key = Column(String(512), nullable=False)  # encrypted
    available_models = Column(MySQLJSON, nullable=False)  # ["gpt-4o", "gpt-4o-mini"]
    is_default = Column(Boolean, default=False, index=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(String(10), nullable=True)  # Store as string: "0.7"
    is_active = Column(Boolean, default=True, index=True)
    is_crm_flow_active = Column(Boolean, default=False, index=True)  # CRM flow activation
    crm_accounts_ids = Column(String(1000), nullable=True)  # Comma-separated account IDs
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    created_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    updated_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", backref="llm_credentials")
    creator = relationship("User", foreign_keys=[created_by], backref="created_llm_credentials")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_llm_credentials")

class ChatAttachments(Base):
    """
    Model for storing chat attachments (S3 URLs) linked to chat sessions and messages
    """
    __tablename__ = "chat_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(String(255), nullable=False, index=True)
    message_id = Column(String(255), nullable=False, index=True)  # This is the event_id
    user_id = Column(String(255), nullable=False, index=True)
    s3_url = Column(Text, nullable=False)
    file_name = Column(String(500), nullable=True)
    file_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add indexes for better query performance
    __table_args__ = (
        Index('idx_chat_session_message', 'chat_session_id', 'message_id'),
        Index('idx_user_session', 'user_id', 'chat_session_id'),
    )
    

class SessionMode(Base):
    __tablename__ = "session_modes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    mode = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<SessionMode(session_id='{self.session_id}', mode='{self.mode}')>"
    
class EmailInboxConfig(Base):
    __tablename__ = "email_inbox_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_email = Column(String(255), nullable=False, index=True)
    password = Column(String(255), nullable=False)
    imap_server = Column(String(255), nullable=False)
    imap_port = Column(Integer, nullable=False, default=993)
    company_id = Column(String(100), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resume_parser_access_token = Column(String(255), nullable=True)
    llm_key = Column(String(512), nullable=True)
    llm_base_url = Column(String(255), nullable=True)

# New tables for enhanced agent system
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(255), nullable=False, index=True)  # Remove unique constraint
    origin = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    company_id = Column(String(100), nullable=True, index=True)  # External company identifier
    created_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    updated_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_companies")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_companies")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True, index=True)
    agent_type = Column(String(20), default='primary', index=True)  # 'primary', 'sub_agent', 'tool'
    default_model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    capabilities = Column(MySQLJSON, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referencing relationship
    children = relationship("Agent", backref="parent", remote_side=[id])


class AgentMapping(Base):
    __tablename__ = "agent_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False, index=True)
    llm_credentials_id = Column(Integer, ForeignKey('llm_credentials.id'), nullable=False, index=True)
    preferred_model = Column(String(100), nullable=True)  # Override for this company-agent combo
    selected_model = Column(String(100), nullable=True)  # Currently selected model for this mapping
    custom_system_prompt = Column(Text, nullable=True)  # Company-specific prompt override
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=1)  # For ordering
    created_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    updated_by = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", backref="agent_mappings")
    agent = relationship("Agent", backref="company_mappings")
    llm_credentials = relationship("LLMCredentials", backref="agent_mappings")
    creator = relationship("User", foreign_keys=[created_by], backref="created_agent_mappings")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_agent_mappings")
    
    # Ensure unique company-agent combination
    __table_args__ = (
        Index('idx_company_agent_unique', 'company_id', 'agent_id', unique=True),
        Index('idx_company_agent_active', 'company_id', 'agent_id', 'is_active'),
        Index('idx_company_credentials', 'company_id', 'llm_credentials_id'),
    )
class NetworkActivityLog(Base):
    """
    Model for storing network activity logs for security monitoring.
    Captures IP addresses, device information, browser details, and user agent strings
    for all API endpoint requests.
    """
    __tablename__ = "network_activity_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False, index=True)  # GET, POST, DELETE, etc.
    ip_address = Column(String(45), nullable=True, index=True)  # IPv4 or IPv6
    forwarded_for = Column(String(255), nullable=True)  # X-Forwarded-For header
    user_agent = Column(Text, nullable=True)  # Full user agent string
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet, bot
    browser = Column(String(100), nullable=True)  # Chrome, Firefox, Safari, etc.
    browser_version = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)  # Operating system
    os_version = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=True)  # Platform details
    user_id = Column(String(255), nullable=True, index=True)  # User identifier if authenticated
    session_id = Column(String(255), nullable=True, index=True)  # Session identifier
    company_id = Column(String(100), nullable=True, index=True)  # Company identifier
    origin = Column(String(255), nullable=True)  # Request origin
    referer = Column(String(500), nullable=True)  # HTTP Referer
    host = Column(String(255), nullable=True)  # Request host
    status_code = Column(Integer, nullable=True)  # Response status code
    request_id = Column(String(100), nullable=True, index=True)  # Unique request identifier
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Add composite indexes for better query performance
    __table_args__ = (
        Index('idx_endpoint_created_at', 'endpoint', 'created_at'),
        Index('idx_user_company', 'user_id', 'company_id'),
        Index('idx_ip_created_at', 'ip_address', 'created_at'),
    )

class EventBackup(Base):
    """
    Event backup model - stores deleted events from the events table.
    This table preserves conversation history that has been cleaned up from the main events table.
    """
    __tablename__ = "events_backup"

    id = Column(String(128), primary_key=True, index=True)
    app_name = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    session_id = Column(String(128), nullable=False)
    invocation_id = Column(String(256), nullable=False)
    author = Column(String(256), nullable=False)
    branch = Column(String(256))
    timestamp = Column(DateTime, nullable=False)
    content = Column(Text)  # LONGTEXT in MySQL - JSON will be serialized as string
    actions = Column(LargeBinary)  # BLOB in MySQL - stores binary pickled data
    long_running_tool_ids_json = Column(Text)
    grounding_metadata = Column(Text)  # LONGTEXT in MySQL
    partial = Column(Boolean)  # TINYINT in MySQL
    turn_complete = Column(Boolean)  # TINYINT in MySQL
    error_code = Column(String(256))
    error_message = Column(String(1024))
    interrupted = Column(Boolean)  # TINYINT in MySQL
    backed_up_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When it was backed up
    
    # Add indexes for better query performance
    __table_args__ = (
        Index('idx_session_id', 'session_id'),
        Index('idx_backed_up_at', 'backed_up_at'),
        Index('idx_session_backed_up', 'session_id', 'backed_up_at'),
    )

    def __repr__(self):
        return f"<EventBackup(id={self.id}, app_name='{self.app_name}', session_id='{self.session_id}')>"
class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(String(255), ForeignKey("iats_user_sessions.session_id"), nullable=False, index=True)
    message_id = Column(String(255), nullable=False, index=True)
    company_id = Column(String(100), nullable=True, index=True)
    origin = Column(String(255), nullable=True, index=True)
    thumbs_up = Column(Boolean, nullable=False, default=False)
    thumbs_down = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_feedback_session_message', 'session_id', 'message_id', unique=True),
        Index('idx_feedback_company_created', 'company_id', 'created_at'),
    )
