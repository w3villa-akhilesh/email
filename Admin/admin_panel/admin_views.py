"""
SQLAdmin views configuration for beautiful admin interface
"""

from sqladmin import ModelView
from models import (
    User, Event, LLMCredentials, SessionMode, ChatAttachment, 
    CompanyIntegrationConfig, EmailInboxConfig, IATSUserSession, 
    IATSLLMCredentials, Session
)
from typing import Any
from starlette.requests import Request

class UserAdmin(ModelView, model=User):
    """Admin view for User model"""
    
    # Basic configuration
    name = "Users"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    
    # Column configuration
    column_list = [
        User.id, 
        User.kivo_id, 
        User.firstName, 
        User.email, 
        User.timeZone
    ]
    
    # Exclude sensitive fields from display and forms
    column_details_exclude_list = [User.refresh_token, User.access_token, User.dp_url_small]
    form_excluded_columns = [User.refresh_token, User.access_token]
    
    # Search and sort configuration
    column_searchable_list = [User.firstName, User.email, User.kivo_id]
    column_sortable_list = [User.id, User.firstName, User.email]
    column_default_sort = [(User.id, False)]
    
    # Labels for better UX
    column_labels = {
        User.id: "ID",
        User.kivo_id: "Kivo ID",
        User.firstName: "First Name",
        User.email: "Email Address",
        User.timeZone: "Timezone"
    }
    
    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]

class EventAdmin(ModelView, model=Event):
    """Admin view for Event model"""
    
    # Basic configuration
    name = "Events"
    name_plural = "Events"
    icon = "fa-solid fa-calendar-days"
    
    # Column configuration
    column_list = [
        Event.id,
        Event.app_name,
        Event.user_id,
        Event.session_id,
        Event.author,
        Event.timestamp,
        Event.turn_complete,
        Event.error_code
    ]
    
    # Show all fields by default, no exclusions needed
    
    # Search and sort configuration
    column_searchable_list = [
        Event.app_name, 
        Event.user_id, 
        Event.session_id, 
        Event.author
    ]
    column_sortable_list = [
        Event.id, 
        Event.app_name, 
        Event.timestamp,
        Event.user_id
    ]
    column_default_sort = [(Event.timestamp, True)]  # Most recent first
    
    # Labels for better UX
    column_labels = {
        Event.id: "Event ID",
        Event.app_name: "Application",
        Event.user_id: "User ID",
        Event.session_id: "Session ID",
        Event.invocation_id: "Invocation ID",
        Event.author: "Author",
        Event.timestamp: "Timestamp",
        Event.content: "Event Content"
    }
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100, 200]
    
    # Custom formatting for content field
    column_formatters = {
        Event.content: lambda m, a: str(m.content)[:100] + "..." if m.content else "No content"
    }


class LLMCredentialsAdmin(ModelView, model=LLMCredentials):
    """Admin view for LLM Credentials model"""
    
    # Basic configuration
    name = "LLM Credentials"
    name_plural = "LLM Credentials"
    icon = "fa-solid fa-key"
    
    # Column configuration
    column_list = [
        LLMCredentials.id,
        LLMCredentials.company_id,
        LLMCredentials.app_name,
        LLMCredentials.llm_model,
        LLMCredentials.origin,
        LLMCredentials.created_at
    ]
    
    # Exclude sensitive API keys from display (but allow in forms with password type)
    column_details_exclude_list = [LLMCredentials.llm_key]
    
    # Use password input for sensitive fields
    form_widget_args = {
        "llm_key": {"type": "password", "class": "form-control"}
    }
    
    # Search and sort configuration
    column_searchable_list = [
        LLMCredentials.company_id,
        LLMCredentials.app_name,
        LLMCredentials.llm_model,
        LLMCredentials.origin
    ]
    column_sortable_list = [
        LLMCredentials.id,
        LLMCredentials.company_id,
        LLMCredentials.app_name,
        LLMCredentials.created_at
    ]
    column_default_sort = [(LLMCredentials.created_at, True)]
    
    # Labels for better UX
    column_labels = {
        LLMCredentials.id: "ID",
        LLMCredentials.company_id: "Company ID",
        LLMCredentials.app_name: "Application Name",
        LLMCredentials.llm_model: "LLM Model",
        LLMCredentials.llm_key: "LLM API Key",
        LLMCredentials.llm_base_url: "Base URL",
        LLMCredentials.origin: "Origin",
        LLMCredentials.created_at: "Created",
        LLMCredentials.updated_at: "Updated"
    }
    
    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]
    
    # Custom formatting for content display
    column_formatters = {
        LLMCredentials.llm_key: lambda m, a: "****" + str(m.llm_key)[-4:] if m.llm_key else "Not set"
    }

class SessionModeAdmin(ModelView, model=SessionMode):
    """Admin view for Session Mode model"""
    
    # Basic configuration
    name = "Session Modes"
    name_plural = "Session Modes"
    icon = "fa-solid fa-cog"
    
    # Column configuration
    column_list = [
        SessionMode.id,
        SessionMode.session_id,
        SessionMode.mode
    ]
    
    # Search and sort configuration
    column_searchable_list = [SessionMode.session_id, SessionMode.mode]
    column_sortable_list = [SessionMode.id, SessionMode.session_id, SessionMode.mode]
    column_default_sort = [(SessionMode.id, False)]
    
    # Labels for better UX
    column_labels = {
        SessionMode.id: "ID",
        SessionMode.session_id: "Session ID",
        SessionMode.mode: "Mode"
    }
    
    # Pagination
    page_size = 30
    page_size_options = [15, 30, 50, 100]

class ChatAttachmentAdmin(ModelView, model=ChatAttachment):
    """Admin view for Chat Attachments"""
    name = "Chat Attachments"
    icon = "fa-solid fa-paperclip"
    
    column_list = [ChatAttachment.id, ChatAttachment.file_name, ChatAttachment.user_id, 
                   ChatAttachment.file_type, ChatAttachment.file_size, ChatAttachment.created_at]
    column_searchable_list = [ChatAttachment.file_name, ChatAttachment.user_id, ChatAttachment.file_type]
    column_sortable_list = [ChatAttachment.id, ChatAttachment.created_at, ChatAttachment.file_size]
    column_default_sort = [(ChatAttachment.created_at, True)]
    page_size = 50

class CompanyIntegrationConfigAdmin(ModelView, model=CompanyIntegrationConfig):
    """Admin view for Company Integration Config"""
    name = "Company Integration Config"
    icon = "fa-solid fa-building"
    
    column_list = [CompanyIntegrationConfig.id, CompanyIntegrationConfig.company_id, 
                   CompanyIntegrationConfig.resume_parser_api_url, CompanyIntegrationConfig.created_at]
    column_details_exclude_list = [CompanyIntegrationConfig.resume_parser_access_token]
    column_searchable_list = [CompanyIntegrationConfig.company_id]
    page_size = 25

class EmailInboxConfigAdmin(ModelView, model=EmailInboxConfig):
    """Admin view for Email Inbox Config"""
    name = "Email Inbox Config"
    icon = "fa-solid fa-envelope"
    
    column_list = [EmailInboxConfig.id, EmailInboxConfig.account_email, 
                   EmailInboxConfig.company_id, EmailInboxConfig.is_active, EmailInboxConfig.created_at]
    column_details_exclude_list = [EmailInboxConfig.password, EmailInboxConfig.llm_key, 
                                   EmailInboxConfig.resume_parser_access_token]
    column_searchable_list = [EmailInboxConfig.account_email, EmailInboxConfig.company_id]
    page_size = 25
    
    form_widget_args = {
        "password": {"type": "password"},
        "llm_key": {"type": "password"},
        "resume_parser_access_token": {"type": "password"}
    }

class IATSUserSessionAdmin(ModelView, model=IATSUserSession):
    """Admin view for IATS User Sessions"""
    name = "IATS User Sessions"
    icon = "fa-solid fa-users-cog"
    
    column_list = [IATSUserSession.session_id, IATSUserSession.user_id, 
                   IATSUserSession.mode, IATSUserSession.app_name, IATSUserSession.created_at]
    column_searchable_list = [IATSUserSession.session_id, IATSUserSession.user_id, IATSUserSession.mode]
    column_sortable_list = [IATSUserSession.created_at, IATSUserSession.session_id]
    page_size = 50

class IATSLLMCredentialsAdmin(ModelView, model=IATSLLMCredentials):
    """Admin view for IATS LLM Credentials"""
    name = "IATS LLM Credentials"
    icon = "fa-solid fa-key"
    
    column_list = [IATSLLMCredentials.id, IATSLLMCredentials.company_id, 
                   IATSLLMCredentials.app_name, IATSLLMCredentials.llm_model, IATSLLMCredentials.created_at]
    column_details_exclude_list = [IATSLLMCredentials.llm_key]
    column_searchable_list = [IATSLLMCredentials.company_id, IATSLLMCredentials.app_name]
    page_size = 25
    
    form_widget_args = {
        "llm_key": {"type": "password"}
    }

class SessionAdmin(ModelView, model=Session):
    """Admin view for Sessions"""
    name = "Sessions"
    icon = "fa-solid fa-desktop"
    
    column_list = [Session.id, Session.app_name, Session.user_id, 
                   Session.create_time, Session.update_time]
    column_searchable_list = [Session.id, Session.app_name, Session.user_id]
    column_sortable_list = [Session.create_time, Session.update_time]
    column_default_sort = [(Session.update_time, True)]
    page_size = 50

# Export all admin views
admin_views = [
    UserAdmin,
    EventAdmin,
    LLMCredentialsAdmin,
    SessionModeAdmin,
    ChatAttachmentAdmin,
    CompanyIntegrationConfigAdmin,
    EmailInboxConfigAdmin,
    IATSUserSessionAdmin,
    IATSLLMCredentialsAdmin,
    SessionAdmin
]
