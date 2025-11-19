"""
GitHub MCP Connection via stdio
Connects to the official GitHub MCP server (@modelcontextprotocol/server-github)
using stdin/stdout communication.
"""

import os
from typing import Optional
from app.services.mcp_connection_stdio import connect_to_stdio_mcp_server
from app.utils.logger import logger


async def connect_to_github_mcp_stdio(
    session_id: Optional[str] = None,
    tool_filter: Optional[str] = None
):
    """
    Connect to the official GitHub MCP server via stdio.
    
    This connects to @modelcontextprotocol/server-github which communicates
    through stdin/stdout instead of HTTP/SSE.
    
    Args:
        session_id: Optional session identifier for logging
        tool_filter: Optional filter string for tool names
        
    Returns:
        MCPToolset with GitHub tools from the official server
        
    Environment Variables Required:
        GITHUB_TOKEN: GitHub Personal Access Token
        
    Example:
        >>> toolset = await connect_to_github_mcp_stdio(session_id="abc123")
        >>> # toolset now contains official GitHub MCP tools
    """
    
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        logger.error("GITHUB_TOKEN not found in environment variables")
        logger.error("Please set GITHUB_TOKEN in your .env file")
        logger.error("Get token from: https://github.com/settings/tokens")
        return None
    
    logger.info("=" * 60)
    logger.info("Connecting to Official GitHub MCP Server (stdio mode)")
    logger.info("=" * 60)
    logger.info(f"Token: {github_token[:10]}... (first 10 chars)")
    if session_id:
        logger.info(f"Session: {session_id}")
    
    # Command to run the official GitHub MCP server
    # This is the same command used by Cursor IDE and Claude Desktop
    command = ["npx", "@modelcontextprotocol/server-github"]
    
    # Environment variables for the GitHub MCP server
    # The official server uses GITHUB_PERSONAL_ACCESS_TOKEN
    env_vars = {
        "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
    }
    
    logger.info(f"Command: {' '.join(command)}")
    logger.info("Establishing stdio connection...")
    
    # Connect to the official GitHub MCP server via stdio
    # Note: Don't use tool_filter as GitHub MCP tools don't have "github" in their names
    # Tool names are like: create_or_update_file, search_repositories, get_file_contents, etc.
    toolset = await connect_to_stdio_mcp_server(
        command=command,
        env_vars=env_vars,
        tool_filter=None,  # Get all tools from GitHub MCP server
        session_id=session_id,
        timeout=60
    )
    
    if toolset:
        logger.info("✅ Successfully connected to official GitHub MCP server")
        logger.info("=" * 60)
    else:
        logger.error("❌ Failed to connect to official GitHub MCP server")
        logger.error("=" * 60)
        logger.error("Troubleshooting:")
        logger.error("1. Check if Node.js is installed: node --version")
        logger.error("2. Check if npx is available: npx --version")
        logger.error("3. Verify GITHUB_TOKEN is set correctly")
        logger.error("4. Try running manually: npx @modelcontextprotocol/server-github")
    
    return toolset


async def test_github_mcp_stdio():
    """
    Test function to verify GitHub MCP stdio connection.
    
    Run this to test if the connection works:
        python -c "import asyncio; from app.services.github_mcp_stdio import test_github_mcp_stdio; asyncio.run(test_github_mcp_stdio())"
    """
    logger.info("Testing GitHub MCP stdio connection...")
    
    toolset = await connect_to_github_mcp_stdio(session_id="test")
    
    if toolset:
        logger.info("✅ Test successful! GitHub MCP stdio connection works.")
        
        # Try to close the toolset
        try:
            await toolset.close()
            logger.info("✅ Toolset closed successfully")
        except Exception as e:
            logger.error(f"Error closing toolset: {e}")
    else:
        logger.error("❌ Test failed! Could not connect to GitHub MCP server.")
    
    return toolset is not None

