from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams
from app.utils.logger import logger
from app.services.email_notifier import send_exception_email
from app.services.mcp_auth import authenticate_mcp_servers
from dotenv import load_dotenv
import json
from fastmcp import Client, FastMCP
from fastmcp.client.transports import SSETransport


load_dotenv()

# setting up connection with mcp server, loading tools 
async def connect_to_mcp_server(server_url=None, tool_filter=None, agent_type=None, exclude_tool_type=None, include_tool_type=None) -> MCPToolset:
    """
    Connect to MCP server and load tools.
    
    Args:
        server_url: URL of the MCP server
        tool_filter: Filter for tools
        agent_type: Type of agent for tool filtering
        exclude_tool_type: Tool types to exclude
        include_tool_type: Tool types to include
        
    Returns:
        MCPToolset with filtered tools
    """
    toolset = None
    try:    
        mcp_token, public_key = await authenticate_mcp_servers()

        if not mcp_token:
            logger.error("Failed to get mcp authentication token or public_key.")
            return
        
        # Test the server
        headers = {
            "Authorization": f"Bearer {mcp_token}",
            "Content-Type": "application/json"
        }
    
        logger.info(f"Connecting to MCP server...")

        toolset = MCPToolset(
            connection_params=SseConnectionParams(
                url=server_url,
                headers=headers,
                timeout=60,
            ),
            tool_filter=tool_filter
        )

        tools_old = await toolset.get_tools()

        transport = SSETransport(
            url=server_url,
            headers=headers,
            sse_read_timeout=30,
        )

        async with Client(
            transport
        ) as client:
            # logging tool names for clarity.
            tools_new = await client.list_tools()
            
        logger.info(f"Filtering tools for agent {agent_type}")
        # Get set of tool names from tools_new where tags contain 'hrms'
        agent_tool_names = set()
        if not agent_type and not include_tool_type and not exclude_tool_type:
            agent_tool_names = {tool.name for tool in tools_new}
        else:
            for tool in tools_new:
                if not (hasattr(tool, 'meta') and tool.meta):
                    continue  

                fastmcp_meta = tool.meta.get('_fastmcp', {})
                tags = fastmcp_meta.get('tags', [])

                if include_tool_type:
                    include_match = any(tag in tags for tag in include_tool_type)
                    if not include_match:
                        continue  

                if exclude_tool_type:
                    exclude_match = any(tag in tags for tag in exclude_tool_type)
                    if exclude_match:
                        continue  

                if agent_type and any(r in tags for r in agent_type):
                    agent_tool_names.add(tool.name)
        
        # Filter tools_old by matching their name against hrms_tool_names
        filtered_tools_old = [tool for tool in tools_old if tool.name in agent_tool_names]
        
        logger.info(f"Filtered tools: {[t.name for t in filtered_tools_old]}")

        tool_data = [tool.name for tool in filtered_tools_old]

        return filtered_tools_old

    except Exception as e:
        logger.error(f"Connection to MCP server failed: {e}", exc_info=False)
        return None
    finally:
        logger.info("user agent execution complete.")
        if toolset:
            try:
                await toolset.close()
                logger.info("Closing toolset from mcp connection")
            except Exception as close_err:
                logger.warning(f"Error closing MCP toolset: {close_err}", exc_info=True)
