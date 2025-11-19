"""
Custom exceptions for the Kivo Agent application.
"""


class LLMKeyNotSetException(Exception):
    """Raised when LLM credentials are not found or not properly configured."""
    
    def __init__(self, app_name: str = None, company_id: str = None, origin: str = None, message: str = None):
        if message:
            self.message = message
        else:
            self.message = f"LLM credentials not found. app_name: {app_name}, company_id: {company_id}, origin: {origin}"
        
        super().__init__(self.message)


class LLMConfigurationException(Exception):
    """Raised when LLM configuration is invalid or missing."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class LLMInitializationException(Exception):
    """Raised when there's an error initializing the LLM engine."""
    
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)
