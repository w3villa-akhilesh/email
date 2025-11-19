from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

# TTSService Enum
class TTSServiceEnum(str, Enum):
    TTS_OPENAI_KEY = "tts_openai_key"
    TTS_CARTESIA_KEY = "tts_cartesia_key"

# Company CRUD Schemas
class CompanyCreate(BaseModel):
    id: int
    name: str
    origin: str
    description: Optional[str] = None
    company_id: Optional[str] = None
    is_active: bool = True

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    origin: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[str] = None
    is_active: Optional[bool] = None

# LLMCredentials CRUD Schemas
class LLMCredentialsNewCreate(BaseModel):
    company_id: int
    provider: str  # 'openai', 'anthropic', etc.
    base_url: str
    api_key: str
    available_models: List[str]  # ["gpt-4o", "gpt-4o-mini"]
    is_default: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[str] = None  # Store as string: "0.7"
    tts_service: Optional[str] = None  # Can be 'tts_openai_key', 'tts_cartesia_key', or None
    cartesia_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    is_crm_flow_active: bool = False
    crm_accounts_ids: Optional[str] = None
    tags: Optional[str] = None
    is_active: bool = True

class LLMCredentialsNewUpdate(BaseModel):
    company_id: Optional[int] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    available_models: Optional[List[str]] = None
    is_default: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[str] = None
    tts_service: Optional[str] = None  # Can be 'tts_openai_key', 'tts_cartesia_key', or None
    cartesia_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    is_crm_flow_active: Optional[bool] = None
    crm_accounts_ids: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None

# AgentMapping CRUD Schemas
class AgentMappingCreate(BaseModel):
    company_id: int
    agent_id: int
    llm_credentials_id: int
    preferred_model: Optional[str] = None
    selected_model: Optional[str] = None
    custom_system_prompt: Optional[str] = None
    is_active: bool = True
    priority: int = 1

class AgentMappingUpdate(BaseModel):
    company_id: Optional[int] = None
    agent_id: Optional[int] = None
    llm_credentials_id: Optional[int] = None
    preferred_model: Optional[str] = None
    selected_model: Optional[str] = None
    custom_system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None

# Agent CRUD Schemas
class AgentCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    parent_agent_id: Optional[int] = None
    agent_type: str = 'primary'  # 'primary', 'sub_agent', 'tool'
    default_model: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[dict] = None
    is_active: bool = True

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    parent_agent_id: Optional[int] = None
    agent_type: Optional[str] = None
    default_model: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[dict] = None
    is_active: Optional[bool] = None

# Agent API Key Schemas
class AgentKeyCreate(BaseModel):
    app_name: str
