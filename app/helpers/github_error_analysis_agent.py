import os
import json
import traceback
from typing import Optional, Dict, Any
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from app.services.llm_engine import get_llm_engine
from app.services.my_sql_client import create_db_url
from app.models.schema import balanced_generation_config
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.services.agent_prompt_service import agent_prompt_service
from app.services.github_mcp_stdio import connect_to_github_mcp_stdio
# Email notification is now handled directly in email_notifier.py


async def initiate_github_error_analysis_agent(
    session_id: str,
    company_id: int,
    app_name: str = "github_error_analysis",
    origin: str = "error_handler",
    profile_block: Optional[str] = None,
    preloaded_context: Optional[str] = None,
    mode: str = "api"
):
    """
    Initialize the GitHub Error Analysis Agent with GitHub MCP tools.
    
    This agent connects to a GitHub MCP server to access GitHub tools for reading
    repository files and analyzing errors in the context of the actual codebase.
    
    Args:
        session_id: Unique session identifier
        company_id: Company/account identifier
        app_name: Application name for session management
        origin: Origin of the request
        profile_block: User profile information
        preloaded_context: Additional context to inject
        mode: Operation mode (api, web, etc.)
        
    Returns:
        Kivo_LLMAgent: Configured agent instance
        
    Raises:
        Exception: If agent initialization fails
        
    Production Setup:
        1. Install Node.js 18+ from https://nodejs.org/
        2. Set GITHUB_TOKEN environment variable
        3. The official GitHub MCP server will start automatically via stdio
    """
    github_toolset = None
    try:
        logger.info("Initializing GitHub Error Analysis Agent")
        logger.info("=" * 60)
        logger.info("Using Official GitHub MCP Server")
        logger.info("Server: @modelcontextprotocol/server-github")
        logger.info("Protocol: stdio (stdin/stdout)")
        logger.info("=" * 60)
        
        # Connect to official GitHub MCP server via stdio
        github_toolset = await connect_to_github_mcp_stdio(
            session_id=session_id,
            tool_filter=None
        )
        
        if not github_toolset:
            error_msg = "Failed to connect to official GitHub MCP server"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        
        logger.info("✅ Successfully connected to official GitHub MCP server")
        
        # Get tools from the toolset
        github_tools = await github_toolset.get_tools()
        logger.info(f"✅ Retrieved {len(github_tools)} GitHub tools from MCP server")
        
        # Get LLM engine for the agent dynamically
        github_analysis_model = get_llm_engine(
            agent_name='github_error_analysis_agent',
            company_id=company_id
        )

        # Get dynamic instructions for GitHub Error Analysis agent
        github_analysis_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="github_error_analysis_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        # Create agent WITH GitHub MCP tools
        github_analysis_agent = Kivo_LLMAgent(
            name="github_error_analysis_agent",
            model=github_analysis_model,
            instruction=github_analysis_instructions,
            description=agent_prompt_service.get_agent_description(
                "github_error_analysis_agent",
                company_id
            ),
            output_key="github_error_analysis_response",
            tools=github_tools,  # Pass list of tools, not toolset
            generate_content_config=balanced_generation_config
        )
        
        logger.info("GitHub Error Analysis Agent initialized successfully")
        return github_analysis_agent

    except Exception as e:
        logger.error(f"Error in initiate_github_error_analysis_agent: {e}", exc_info=True)
        raise
    
    finally:
        # Note: Don't close toolset here - it's managed by the agent lifecycle
        pass


async def analyze_error_with_github_context(
    error: Exception,
    error_context: str,
    session_id: str,
    company_id: Optional[int] = None,
    origin: Optional[str] = None,
    repository_owner: Optional[str] = None,
    repository_name: Optional[str] = None,
    file_path: Optional[str] = None,
    network_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze an error using GitHub MCP tools to read relevant files and provide solutions.
    
    This function:
    1. Formats the error details
    2. Invokes the GitHub Error Analysis Agent
    3. Agent uses GitHub MCP tools to read repository files
    4. Returns detailed analysis with solutions
    5. Optionally sends email notification with analysis
    
    Args:
        error: The exception that occurred
        error_context: Context description of where the error occurred
        session_id: Session identifier
        company_id: Company identifier (defaults to env var)
        origin: Request origin
        repository_owner: GitHub repository owner (e.g., "w3villa")
        repository_name: GitHub repository name (e.g., "kivo_agent")
        file_path: Path to the file where error occurred
        network_details: Network/request details
        
    Returns:
        dict: Analysis results containing:
            - analysis: Detailed error analysis and solutions
            - error_type: Type of error
            - error_message: Error message
            - invocation_id: Agent invocation ID
            
    Example:
        ```python
        try:
            # Some code that might fail
            result = risky_operation()
        except Exception as e:
            analysis = await analyze_error_with_github_context(
                error=e,
                error_context="Failed during risky_operation in main.py",
                session_id="session_123",
                company_id=1,
                repository_owner="w3villa",
                repository_name="kivo_agent",
                file_path="main.py"
            )
            logger.info(f"Error analysis: {analysis['analysis']}")
            
        Note:
            This function only performs analysis and returns results.
            Email notifications should be handled by send_exception_email() or
            send_exception_email_async() which automatically includes AI analysis.
        ```
    """
    try:
        logger.info(f"Starting GitHub error analysis for session: {session_id}")
        
        # Use default company_id if not provided
        if company_id is None:
            company_id = int(os.getenv("ACCOUNT_ID", "1"))
        
        # Extract error details
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Build the error context payload
        error_payload = {
            "error_type": error_type,
            "error_message": error_message,
            "error_traceback": error_traceback,
            "context": error_context,
            "session_id": session_id,
            "company_id": company_id,
            "origin": origin or "unknown",
        }
        
        # Add repository details if provided
        if repository_owner:
            error_payload["repository_owner"] = repository_owner
        if repository_name:
            error_payload["repository_name"] = repository_name
        if file_path:
            error_payload["file_path"] = file_path
            
        # Add network details if available
        if network_details:
            error_payload["network_details"] = network_details
        
        # Create profile block with error context
        profile_block = f"""
Error Analysis Context:
- Session ID: {session_id}
- Company ID: {company_id}
- Origin: {origin or 'unknown'}
- Error Type: {error_type}
"""
        
        if repository_owner and repository_name:
            profile_block += f"""
- Repository: {repository_owner}/{repository_name}
"""
        
        if file_path:
            profile_block += f"""
- File Path: {file_path}
"""

        # Prepare the analysis query
        analysis_query = f"""
Please analyze this error and provide actionable solutions:

ERROR DETAILS:
- Type: {error_type}
- Message: {error_message}
- Context: {error_context}

TRACEBACK:
{error_traceback}

REPOSITORY INFORMATION:
"""
        
        if repository_owner and repository_name:
            analysis_query += f"""
- Owner: {repository_owner}
- Repository: {repository_name}
"""
            if file_path:
                analysis_query += f"""
- File Path: {file_path}

Please use the GitHub MCP tools to read the file at '{file_path}' from repository '{repository_owner}/{repository_name}' 
and analyze the error in context. If the error involves other files, read those as well.
"""
        else:
            analysis_query += """
- No repository information provided. Please analyze based on the error details and traceback.
"""

        # Initialize the agent
        agent = await initiate_github_error_analysis_agent(
            session_id=session_id,
            company_id=company_id,
            app_name="github_error_analysis",
            origin=origin or "error_handler",
            profile_block=profile_block,
            preloaded_context=None,
            mode="api"
        )

        # Prepare user input
        llm_query_json = {
            "query": analysis_query,
            "error_details": error_payload
        }
        content = types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(llm_query_json, indent=2))]
        )

        # Create DB session
        db_url = create_db_url()
        if not db_url:
            error_msg = "Invalid database URL"
            logger.error(error_msg)
            raise ValueError(error_msg)

        session_service = DatabaseSessionService(db_url=db_url)
        app_name = "github_error_analysis"
        
        session = await session_service.get_session(
            app_name=app_name,
            user_id=session_id,
            session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name=app_name,
                user_id=session_id,
                session_id=session_id
            )

        # Run the agent with error handling for tool failures
        runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
        response = None
        invocation_id = None
        tool_errors = []
        
        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content
        ):
            invocation_id = event.invocation_id
            
            # Log tool execution events
            if hasattr(event, 'type') and 'tool' in str(event.type).lower():
                logger.debug(f"Tool event: {event.type}")
            
            # Catch tool errors
            if hasattr(event, 'error') and event.error:
                logger.warning(f"Tool error occurred: {event.error}")
                tool_errors.append(str(event.error))
            
            if event.is_final_response():
                logger.info("Final response received from GitHub Error Analysis Agent")
                if event.content and hasattr(event.content, "parts") and event.content.parts:
                    response = event.content.parts[0].text
                    logger.debug(f"Agent analysis response received")
                    break
                else:
                    logger.warning("Event has no content, waiting for valid response...")
                    continue

        # Fallback if no response was set
        if response is None:
            error_msg = "No final response received from the agent"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Parse response
        try:
            analysis_result = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            analysis_result = {"analysis": response}

        # Build result
        result = {
            "status": "success",
            "analysis": analysis_result if isinstance(analysis_result, dict) else {"analysis": analysis_result},
            "error_type": error_type,
            "error_message": error_message,
            "invocation_id": invocation_id,
            "session_id": session_id
        }
        
        logger.info(f"GitHub error analysis completed successfully for session: {session_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_error_with_github_context: {e}", exc_info=True)
        raise

