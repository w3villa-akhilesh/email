from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from .connection import Base
from datetime import datetime

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    kivo_id = Column(String(255), unique=True, index=True, nullable=False)
    firstName = Column(String(255))
    # dp_url_small = Column(String(255))
    email = Column(String(255), unique=True)
    timeZone = Column(String(255))
    refresh_token = Column(String(255))
    access_token = Column(String(255))

    def __repr__(self):
        return f"<User(kivo_id='{self.kivo_id}', firstName='{self.firstName}')>"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    app_name = Column(String(255), nullable=False)
    user_id = Column(String(255))
    session_id = Column(String(255))
    invocation_id = Column(String(255))
    author = Column(String(255))
    timestamp = Column(DateTime, default=func.now())
    content = Column(JSON)
    
class SessionMode(Base):
    __tablename__ = "session_modes" 

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    mode = Column(String(100))

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

class LLMCredentials(Base):
    __tablename__ = "llm_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)  # 'openai', 'anthropic', etc.
    base_url = Column(String(255), nullable=False)
    tts_service = Column(String(20), default=None, nullable=True)
    cartesia_api_key = Column(String(512), nullable=True)
    deepgram_api_key = Column(String(512), nullable=True)
    openai_api_key = Column(String(512), nullable=True)
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

class AgentApiKey(Base):
    __tablename__ = "agent_api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)  # The application that will use this key to call our services
    client_app_name = Column(String(255), nullable=False, index=True)  # Generated API key (unique)
    api_key = Column(String(512), nullable=False, unique=True, index=True)  # Optional active flag to disable a key without deleting it
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AgentApiKey(client_app_name='{self.client_app_name}')>"
class NetworkActivityLog(Base):
    """
    Model for storing network activity logs for security monitoring.
    """
    __tablename__ = "network_activity_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    forwarded_for = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    browser_version = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=True)
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    company_id = Column(String(100), nullable=True, index=True)
    origin = Column(String(255), nullable=True)
    referer = Column(String(500), nullable=True)
    host = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
