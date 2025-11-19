from typing import Dict, Any, Optional
from app.services.dynamic_prompt_factory import prompt_factory
from app.utils.logger import logger
from datetime import datetime

class AgentPromptService:
    """
    Service for managing agent prompts with dynamic content and company-specific configurations
    """
    
    @staticmethod
    def get_agent_prompt(
        agent_name: str,
        company_id: int = None,
        session_id: str = None,
        profile_info: Dict = None,
        preloaded_context: Dict = None,
        mode: str = "web",
        **additional_vars
    ) -> str:
        """
        Get dynamic prompt for an agent with all necessary variables
        
        Args:
            agent_name: Name of the agent
            company_id: Company ID for agent availability checking
            session_id: Current session ID
            profile_info: User profile information
            preloaded_context: Context from previous interactions
            mode: Interaction mode (web, mobile, etc.)
            **additional_vars: Additional template variables
            
        Returns:
            Formatted prompt string
        """
        
        # Prepare template variables
        template_vars = {
            'session_id': session_id or 'unknown',
            'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'profile_info': profile_info or {},
            'preloaded_context': preloaded_context or {},
            'mode': mode,
            'close_match': additional_vars.get('close_match', False),
        }
        
        # Add any additional variables
        template_vars.update(additional_vars)
        
        # Get dynamic prompt
        try:
            prompt = prompt_factory.get_dynamic_prompt(
                agent_name=agent_name,
                company_id=company_id,
                **template_vars
            )
            
            logger.debug(f"Generated dynamic prompt for {agent_name} (company: {company_id})")
            return prompt
            
        except Exception as e:
            logger.error(f"Error generating prompt for {agent_name}: {e}")
            # Return fallback prompt
            return AgentPromptService._get_emergency_fallback_prompt(agent_name, template_vars)
    
    @staticmethod
    def get_agent_description(agent_name: str, company_id: int = None) -> str:
        """Get dynamic agent description"""
        try:
            return prompt_factory.get_agent_description(agent_name, company_id)
        except Exception as e:
            logger.error(f"Error getting description for {agent_name}: {e}")
            return f"AI assistant for {agent_name.replace('_', ' ').title()}"
    
    @staticmethod
    def _get_emergency_fallback_prompt(agent_name: str, template_vars: Dict) -> str:
        """Emergency fallback prompt if all else fails"""
        
        user_name = ""
        if template_vars.get('profile_info') and isinstance(template_vars['profile_info'], dict):
            user_name = template_vars['profile_info'].get('name', '')
            if user_name:
                user_name = f"Hello {user_name}, "
        
        return f"""You are {agent_name.replace('_', ' ').title()}, a professional AI assistant.

                {user_name}I'm here to help you with your queries.

                Current session: {template_vars.get('session_id', 'unknown')}
                Date: {template_vars.get('current_date', 'unknown')}

                Guidelines:
                1. Be professional and helpful
                2. Handle user queries within your capabilities
                3. If you need to transfer to another agent, inform the user appropriately
                4. Never mention technical details or internal processes

                How can I assist you today?
                """

# Global service instance
agent_prompt_service = AgentPromptService()
