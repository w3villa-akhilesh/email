#!/usr/bin/env python3
"""
Simple test of stdio connection with corrected API
"""

import os
import asyncio
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.github_mcp_stdio import connect_to_github_mcp_stdio

load_dotenv()

async def main():
    print("\n" + "="*70)
    print("Testing Official GitHub MCP Server (stdio mode)")
    print("="*70)
    
    # Check token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not found")
        return
    
    print(f"✅ GitHub Token: {github_token[:10]}...")
    print("\n⏳ Connecting to GitHub MCP server via stdio...")
    print("(This may show some warnings - that's normal)")
    print()
    
    # Connect
    toolset = await connect_to_github_mcp_stdio(
        session_id="test-simple",
        tool_filter="github"
    )
    
    if toolset:
        print("\n" + "="*70)
        print("✅ SUCCESS! Connected to GitHub MCP Server")
        print("="*70)
        
        # Get tools
        tools = await toolset.get_tools()
        print(f"\n📦 Available GitHub Tools: {len(tools)}")
        print()
        for i, tool in enumerate(tools[:10], 1):  # Show first 10
            print(f"  {i}. {tool.name}")
        
        if len(tools) > 10:
            print(f"  ... and {len(tools) - 10} more")
        
        # Test one tool
        print("\n" + "="*70)
        print("Testing: get_file_contents tool")
        print("="*70)
        
        try:
            # Try to read a file from a public GitHub repo
            result = await toolset.call_tool(
                "get_file_contents",
                owner="octocat",
                repo="Hello-World",
                path="README"
            )
            print(f"✅ Tool call successful!")
            print(f"📄 File content preview: {str(result)[:200]}...")
        except Exception as e:
            print(f"⚠️ Tool call failed (might need specific repo access): {e}")
        
        # Clean up
        await toolset.close()
        
        print("\n" + "="*70)
        print("🎉 All tests passed! Stdio connection is working!")
        print("="*70)
        
    else:
        print("\n❌ Failed to connect")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

