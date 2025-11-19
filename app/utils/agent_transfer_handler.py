from typing import Dict, Any, Optional, List
from app.services.dynamic_prompt_factory import prompt_factory
from app.utils.logger import logger
import re

class AgentTransferHandler:
    """
    Handles agent transfer errors and provides graceful fallbacks
    """
    
    @staticmethod
    def is_agent_not_found_error(error_message: str) -> bool:
        """Check if error is related to agent not found in tree"""
        error_patterns = [
            r"Agent .+ not found in the agent tree",
            r"Agent .+ not found",
            r"not found in the agent tree",
            r"ValueError: Agent .+ not found"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def extract_agent_name_from_error(error_message: str) -> Optional[str]:
        """Extract agent name from error message"""
        patterns = [
            r"Agent (\w+) not found in the agent tree",
            r"Agent (\w+) not found",
            r"ValueError: Agent (\w+) not found"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def handle_agent_transfer_error(
        error_message: str, 
        current_agent: str, 
        company_id: int = None,
        session_context: Dict = None
    ) -> Dict[str, Any]:
        """
        Handle agent transfer error and provide graceful response
        
        Returns:
            {
                'should_handle': bool,
                'response_message': str,
                'suggested_agent': str or None,
                'fallback_action': str
            }
        """
        
        if not AgentTransferHandler.is_agent_not_found_error(error_message):
            return {'should_handle': False}
        
        requested_agent = AgentTransferHandler.extract_agent_name_from_error(error_message)
        
        # Validate transfer and get suggestions
        validation_result = prompt_factory.validate_agent_transfer(
            from_agent=current_agent,
            to_agent=requested_agent or "unknown",
            company_id=company_id
        )
        
        # Generate user-friendly response
        if validation_result['suggested_agent']:
            response_message = AgentTransferHandler._generate_graceful_response(
                requested_agent=requested_agent,
                suggested_agent=validation_result['suggested_agent'],
                current_agent=current_agent,
                session_context=session_context
            )
            
            return {
                'should_handle': True,
                'response_message': response_message,
                'suggested_agent': validation_result['suggested_agent'],
                'fallback_action': 'transfer_to_suggested',
                'available_agents': validation_result['available_agents']
            }
        else:
            # No suitable alternative found
            response_message = AgentTransferHandler._generate_fallback_response(
                current_agent=current_agent,
                session_context=session_context
            )
            
            return {
                'should_handle': True,
                'response_message': response_message,
                'suggested_agent': None,
                'fallback_action': 'handle_locally',
                'available_agents': validation_result.get('available_agents', [])
            }
    
    @staticmethod
    def _generate_graceful_response(
        requested_agent: str, 
        suggested_agent: str, 
        current_agent: str,
        session_context: Dict = None
    ) -> str:
        """Generate a graceful response for agent transfer issues"""
        
        # Get user name from session context if available
        user_name = ""
        if session_context and 'profile_info' in session_context:
            profile_info = session_context['profile_info']
            if isinstance(profile_info, dict) and 'name' in profile_info:
                user_name = f"{profile_info['name']}, "
        
        # Simple response without complex mapping
        return f"{user_name}I'll help you with your query through our available system."
    
    @staticmethod
    def _generate_fallback_response(current_agent: str, session_context: Dict = None) -> str:
        """Generate fallback response when no suitable agent is available"""
        return "I'll do my best to help you with your query. Please provide more details about what you need assistance with."
    

# Global handler instance
transfer_handler = AgentTransferHandler()
