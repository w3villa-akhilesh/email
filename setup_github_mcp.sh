#!/bin/bash

# GitHub MCP Server Setup Script for KIVO Agent
# This script helps you set up the GitHub MCP server for production use

set -e

echo "=================================="
echo "GitHub MCP Server Setup for KIVO Agent"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Node.js is installed
echo "Checking prerequisites..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js version is too old (need 18+)${NC}"
    echo "Current version: $(node -v)"
    exit 1
fi

echo -e "${GREEN}✅ Node.js version: $(node -v)${NC}"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ npm version: $(npm -v)${NC}"
echo ""

# Ask for GitHub token
echo "=================================="
echo "GitHub Token Setup"
echo "=================================="
echo ""
echo "You need a GitHub Personal Access Token with 'repo' scope."
echo "Get one here: https://github.com/settings/tokens"
echo ""
read -p "Enter your GitHub Personal Access Token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ GitHub token is required${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token received${NC}"
echo ""

# Ask for repository details
echo "=================================="
echo "Repository Configuration"
echo "=================================="
echo ""
read -p "Enter your GitHub username or organization (default: w3villa): " REPO_OWNER
REPO_OWNER=${REPO_OWNER:-w3villa}

read -p "Enter your repository name (default: kivo_agent): " REPO_NAME
REPO_NAME=${REPO_NAME:-kivo_agent}

echo -e "${GREEN}✅ Repository: ${REPO_OWNER}/${REPO_NAME}${NC}"
echo ""

# Ask for MCP server port
read -p "Enter MCP server port (default: 9025): " MCP_PORT
MCP_PORT=${MCP_PORT:-9025}

echo ""

# Update or create .env file
echo "=================================="
echo "Updating .env file"
echo "=================================="
echo ""

ENV_FILE=".env"

# Backup existing .env if it exists
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}ℹ️  Backed up existing .env file${NC}"
fi

# Update or add configuration
if ! grep -q "GITHUB_MCP_SERVER_URL" "$ENV_FILE" 2>/dev/null; then
    echo "" >> "$ENV_FILE"
    echo "# GitHub MCP Server Configuration" >> "$ENV_FILE"
    echo "GITHUB_MCP_SERVER_URL=http://localhost:${MCP_PORT}/sse" >> "$ENV_FILE"
else
    sed -i.bak "s|GITHUB_MCP_SERVER_URL=.*|GITHUB_MCP_SERVER_URL=http://localhost:${MCP_PORT}/sse|" "$ENV_FILE"
fi

if ! grep -q "GITHUB_TOKEN" "$ENV_FILE" 2>/dev/null; then
    echo "GITHUB_TOKEN=${GITHUB_TOKEN}" >> "$ENV_FILE"
else
    sed -i.bak "s|GITHUB_TOKEN=.*|GITHUB_TOKEN=${GITHUB_TOKEN}|" "$ENV_FILE"
fi

if ! grep -q "GITHUB_REPOSITORY_OWNER" "$ENV_FILE" 2>/dev/null; then
    echo "GITHUB_REPOSITORY_OWNER=${REPO_OWNER}" >> "$ENV_FILE"
else
    sed -i.bak "s|GITHUB_REPOSITORY_OWNER=.*|GITHUB_REPOSITORY_OWNER=${REPO_OWNER}|" "$ENV_FILE"
fi

if ! grep -q "GITHUB_REPOSITORY_NAME" "$ENV_FILE" 2>/dev/null; then
    echo "GITHUB_REPOSITORY_NAME=${REPO_NAME}" >> "$ENV_FILE"
else
    sed -i.bak "s|GITHUB_REPOSITORY_NAME=.*|GITHUB_REPOSITORY_NAME=${REPO_NAME}|" "$ENV_FILE"
fi

if ! grep -q "ENABLE_AI_ERROR_ANALYSIS" "$ENV_FILE" 2>/dev/null; then
    echo "ENABLE_AI_ERROR_ANALYSIS=true" >> "$ENV_FILE"
fi

echo -e "${GREEN}✅ .env file updated${NC}"
echo ""

# Create systemd service file
echo "=================================="
echo "Creating systemd service"
echo "=================================="
echo ""

read -p "Do you want to create a systemd service for production? (y/n): " CREATE_SERVICE

if [ "$CREATE_SERVICE" = "y" ] || [ "$CREATE_SERVICE" = "Y" ]; then
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)
    
    SERVICE_FILE="/tmp/github-mcp.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GitHub MCP Server for KIVO Agent
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
Environment="GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}"
Environment="PORT=${MCP_PORT}"
ExecStart=/usr/bin/npx @modelcontextprotocol/server-github
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}✅ Service file created at ${SERVICE_FILE}${NC}"
    echo ""
    echo "To install the service, run these commands as root:"
    echo ""
    echo -e "${YELLOW}sudo cp ${SERVICE_FILE} /etc/systemd/system/github-mcp.service${NC}"
    echo -e "${YELLOW}sudo systemctl daemon-reload${NC}"
    echo -e "${YELLOW}sudo systemctl enable github-mcp${NC}"
    echo -e "${YELLOW}sudo systemctl start github-mcp${NC}"
    echo ""
fi

# Test the setup
echo "=================================="
echo "Testing GitHub MCP Server"
echo "=================================="
echo ""

read -p "Do you want to start the GitHub MCP server now for testing? (y/n): " START_TEST

if [ "$START_TEST" = "y" ] || [ "$START_TEST" = "Y" ]; then
    echo -e "${YELLOW}Starting GitHub MCP server on port ${MCP_PORT}...${NC}"
    echo "Press Ctrl+C to stop the server"
    echo ""
    
    GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN PORT=$MCP_PORT npx @modelcontextprotocol/server-github
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo -e "${GREEN}✅ Configuration saved to .env${NC}"
echo -e "${GREEN}✅ GitHub MCP server configured on port ${MCP_PORT}${NC}"
echo ""
echo "Next steps:"
echo "1. Start the GitHub MCP server:"
echo "   ${YELLOW}GITHUB_PERSONAL_ACCESS_TOKEN=\$GITHUB_TOKEN PORT=${MCP_PORT} npx @modelcontextprotocol/server-github${NC}"
echo ""
echo "2. In another terminal, start your KIVO Agent:"
echo "   ${YELLOW}python -m uvicorn main:app --reload${NC}"
echo ""
echo "3. Test error analysis by adding file_path to send_exception_email():"
echo "   ${YELLOW}send_exception_email(error, context, session_id, file_path='main.py')${NC}"
echo ""
echo "For production deployment, see: GITHUB_MCP_PRODUCTION_SETUP.md"
echo ""



