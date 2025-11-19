#!/bin/bash

# Local Development Startup Script for GitHub Error Analysis
# This script starts both GitHub MCP server and KIVO Agent locally

set -e

echo "=================================="
echo "🏠 KIVO Agent - Local Development"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables
if [ -f .env ]; then
    # Load .env file properly, handling comments and special characters
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^#.* ]] && continue
        # Remove leading/trailing whitespace and quotes
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs | sed 's/^["'"'"']//;s/["'"'"']$//')
        # Export the variable
        export "$key=$value"
    done < .env
    echo -e "${GREEN}✅ Loaded .env file${NC}"
else
    echo -e "${YELLOW}⚠️  No .env file found${NC}"
fi

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ GITHUB_TOKEN not set in .env${NC}"
    echo ""
    echo "Please add to .env:"
    echo "  GITHUB_TOKEN=ghp_your_token_here"
    echo ""
    echo "Get token: https://github.com/settings/tokens"
    exit 1
fi

echo -e "${GREEN}✅ GitHub token configured${NC}"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not installed${NC}"
    echo "Install from: https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}✅ Node.js $(node -v)${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not installed${NC}"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${GREEN}✅ Python $($PYTHON_CMD --version)${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    if [ ! -z "$MCP_PID" ]; then
        echo "Stopping GitHub MCP Server (PID: $MCP_PID)"
        kill $MCP_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$KIVO_PID" ]; then
        echo "Stopping KIVO Agent (PID: $KIVO_PID)"
        kill $KIVO_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
    exit 0
}

# Trap cleanup on exit
trap cleanup EXIT INT TERM

# Note: GitHub MCP Server (stdio mode)
echo "=================================="
echo "ℹ️  GitHub MCP Server"
echo "=================================="
echo ""
echo "Using official GitHub MCP server via stdio"
echo "Server: @modelcontextprotocol/server-github"
echo "Protocol: stdio (automatically started by application)"
echo ""
echo -e "${GREEN}✅ No manual server start needed${NC}"
echo ""

# Start KIVO Agent
echo "=================================="
echo "🚀 Starting KIVO Agent"
echo "=================================="
echo ""

# Update GITHUB_MCP_SERVER_URL for local development
export GITHUB_MCP_SERVER_URL="http://localhost:$MCP_PORT/sse"

KIVO_PORT=${KIVO_PORT:-8080}

echo "Starting on port $KIVO_PORT..."
echo -e "${BLUE}Logs will appear below:${NC}"
echo ""
echo "-----------------------------------"

# Start KIVO Agent in foreground
$PYTHON_CMD -m uvicorn main:app --reload --host 0.0.0.0 --port $KIVO_PORT

# This line will only be reached if uvicorn exits
echo ""
echo -e "${YELLOW}⚠️  KIVO Agent stopped${NC}"

