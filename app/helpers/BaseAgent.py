from typing import AsyncGenerator, Any
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types
from google.adk.events import Event
from app.utils.logger import logger
from app.utils.check_multiple_message import check_multiple_message
class Kivo_LLMAgent(LlmAgent):
    """
    Custom agent implementation that extends BaseAgent with additional control logic.
    Provides memory service checking and early termination capabilities.
    """
    
    # Define additional fields as Pydantic fields
    model: Any = None
    description: str = ""
    instruction: str = ""
    tools: list = []
    
    def __init__(self, name: str, model=None, description: str = "", instruction: str = "", tools: list = None, sub_agents: list = None, **kwargs):
        """
        Initialize the custom agent with the same parameters as Agent class.
        
        Args:
            name: Agent name
            model: Model configuration
            description: Agent description
            instruction: Agent instruction
            tools: List of tools available to the agent
        """
        super().__init__(
            name=name,
            model=model,
            description=description,
            instruction=instruction,
            tools=tools or [],
            sub_agents=sub_agents or [],
            **kwargs
        )
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Custom implementation of the agent's async run method with enhanced control.
        
        Args:
            ctx: InvocationContext containing session state and services
            
        Yields:
            Event: Generated events during agent execution
        """
        logger.info(f"BaseAgent _run_async_impl started for agent: {self.name}")
        
        # Check for multiple messages - if True, multiple messages exist so we should block
        has_multiple_messages = check_multiple_message(ctx.session.id)
        
        if has_multiple_messages:
            logger.warning(f"Multiple messages detected for session {ctx.session.id} - blocking {self.name} execution")
            ctx.end_invocation = True  # Signal framework to stop processing
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text="I cannot process this request because you have a new query in the queue. Please wait for the current query to complete.")]
                )
            )
            logger.warning(f"Agent {self.name} execution blocked due to multiple messages")
            return  # Stop this agent's execution
        
        logger.info(f"No blocking conditions detected for {self.name} - proceeding with normal processing")
        
        # Normal agent processing - call the parent implementation
        async for event in super()._run_async_impl(ctx):
            yield event
 