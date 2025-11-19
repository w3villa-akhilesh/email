#!/usr/bin/env python3
"""
Test script for GitHub MCP stdio connection
Tests if the official GitHub MCP server works via stdio

Usage:
    python test_github_mcp_stdio.py
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.github_mcp_stdio import connect_to_github_mcp_stdio
from app.utils.logger import logger


async def test_connection():
    """Test the stdio connection to official GitHub MCP server"""
    
    print("=" * 70)
    print("Testing Official GitHub MCP Server (stdio mode)")
    print("=" * 70)
    print("")
    
    # Check prerequisites
    print("1. Checking prerequisites...")
    
    # Check GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not set in .env")
        print("   Add: GITHUB_TOKEN=ghp_your_token")
        return False
    print(f"   ✅ GitHub token found: {github_token[:10]}...")
    
    # Check Node.js
    import subprocess
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"   ✅ Node.js: {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ Node.js not found")
        print("      Install from: https://nodejs.org/")
        return False
    
    # Check npx
    try:
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        print(f"   ✅ npx: {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ npx not found")
        return False
    
    print("")
    print("2. Connecting to official GitHub MCP server...")
    print("")
    
    # Try to connect
    toolset = await connect_to_github_mcp_stdio(session_id="test")
    
    if toolset:
        print("")
        print("=" * 70)
        print("✅ SUCCESS! Official GitHub MCP server connection works!")
        print("=" * 70)
        print("")
        print("You can now use the official server by setting:")
        print("   USE_OFFICIAL_GITHUB_MCP=true")
        print("in your .env file")
        print("")
        
        # Try to close
        try:
            await toolset.close()
            print("✅ Connection closed successfully")
        except Exception as e:
            print(f"⚠️  Error closing connection: {e}")
        
        return True
    else:
        print("")
        print("=" * 70)
        print("❌ FAILED to connect to official GitHub MCP server")
        print("=" * 70)
        print("")
        print("Troubleshooting:")
        print("1. Check if you can run manually:")
        print(f"   GITHUB_PERSONAL_ACCESS_TOKEN={github_token[:10]}... npx @modelcontextprotocol/server-github")
        print("")
        print("2. Check the logs above for error details")
        print("")
        return False


if __name__ == "__main__":
    print("")
    success = asyncio.run(test_connection())
    print("")
    
    if success:
        print("Next steps:")
        print("1. Add to .env: USE_OFFICIAL_GITHUB_MCP=true")
        print("2. Restart your application")
        print("3. Trigger an error to test AI analysis")
        print("")
        sys.exit(0)
    else:
        print("Fix the issues above and try again.")
        print("")
        print("Or continue using the custom server (default):")
        print("  USE_OFFICIAL_GITHUB_MCP=false")
        print("")
        sys.exit(1)

