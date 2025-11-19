"""
MCP Connection Handler for stdio-based servers
Allows connecting to MCP servers that use stdin/stdout communication
(like the official GitHub MCP server)

This is separate from the SSE-based connection (mcp_connection.py)
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters
from app.utils.logger import logger


async def connect_to_stdio_mcp_server(
    command: List[str],
    env_vars: Optional[Dict[str, str]] = None,
    tool_filter: Optional[str] = None,
    agent_type: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: int = 60
) -> Optional[MCPToolset]:
    """
    Connect to MCP server via stdio (standard input/output).
    
    This allows connection to MCP servers that communicate through stdin/stdout,
    like the official GitHub MCP server from @modelcontextprotocol/server-github.
    
    Args:
        command: Command to run the MCP server (e.g., ["npx", "@modelcontextprotocol/server-github"])
        env_vars: Environment variables to pass to the server process
        tool_filter: Optional filter string for tool names
        agent_type: Optional agent type for filtering tools
        session_id: Optional session identifier
        timeout: Connection timeout in seconds (default: 60)
        
    Returns:
        MCPToolset with tools from the stdio server, or None if connection fails
        
    Example:
        >>> command = ["npx", "@modelcontextprotocol/server-github"]
        >>> env_vars = {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}
        >>> toolset = await connect_to_stdio_mcp_server(command, env_vars)
    """
    toolset = None
    
    try:
        logger.info(f"Connecting to stdio MCP server: {' '.join(command)}")
        
        # Prepare environment variables
        # Use minimal environment - only what MCP server needs
        env = env_vars if env_vars else {}
        if env_vars:
            logger.info(f"Added {len(env_vars)} environment variables")
        
        if session_id:
            logger.info(f"Session ID: {session_id}")
        
        # Create toolset with stdio connection parameters
        # Use StdioServerParameters for proper configuration
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:] if len(command) > 1 else [],
            env=env
        )
        
        toolset = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=server_params,
                timeout=timeout
            )
        )
        
        logger.info("Fetching tools from stdio MCP server...")
        
        # Get tools from the server
        tools_old = await toolset.get_tools()
        
        if not tools_old:
            logger.warning("No tools received from stdio MCP server")
            return None
        
        logger.info(f"Received {len(tools_old)} tools from stdio MCP server")
        
        # Filter tools if needed
        if tool_filter or agent_type:
            logger.info(f"Filtering tools for agent {agent_type} with filter '{tool_filter}'")
            
            filtered_tools = []
            for tool in tools_old:
                tool_name = tool.name.lower()
                
                # Apply tool filter
                if tool_filter and tool_filter.lower() not in tool_name:
                    continue
                
                # Apply agent type filter (if needed)
                # You can customize this based on your agent types
                
                filtered_tools.append(tool)
            
            logger.info(f"Filtered tools: {[t.name for t in filtered_tools]}")
            logger.info(f"Total filtered tools: {len(filtered_tools)}")
        else:
            filtered_tools = tools_old
            logger.info(f"All tools: {[t.name for t in filtered_tools]}")
        
        logger.info("stdio MCP server connection complete")
        
        return toolset
        
    except Exception as e:
        logger.error(f"Connection to stdio MCP server failed: {e}", exc_info=True)
        
        # Close toolset if it was created
        if toolset:
            try:
                logger.info("Closing toolset from stdio MCP connection")
                await toolset.close()
            except Exception as close_error:
                logger.error(f"Error closing toolset: {close_error}")
        
        return None

