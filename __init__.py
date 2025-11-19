"""
Root agent initialization module.
"""
from google.adk.agents.base_agent import BaseAgent
from google.genai import types

class RootAgent(BaseAgent):
    """Basic root agent implementation."""
    
    def __init__(self, name: str = "root_agent", description: str = "Root agent for testing"):
        super().__init__(name=name, description=description)
    
    async def _run_async_impl(self, ctx) -> types.Content:
        """Process incoming messages."""
        message = ctx.user_message
        # For our test case, we'll just return a simple greeting
        if message.text.lower() == "hello":
            return types.Content("Hello! How can I help you today?")
        return types.Content("I'm not sure how to respond to that.")

# Create the root agent instance
root_agent = RootAgent() 