import os 
from dotenv import load_dotenv
load_dotenv()

PM_BOARD_AGENT_NAME="story_validation_sub_agent"
DATA_HANDLER_AGENT_NAME = "Data_Handler_Agent"
TRANSCRIBE_AGENT_NAME="Transcribe_Agent"
RESUME_PARSER_AGENT_NAME="Resume_Parser_Agent"
CALLING_AGENT_NAME="calling_agent"
GITHUB_ERROR_ANALYSIS_AGENT_NAME="github_error_analysis_agent"

ELASTIC_HOST = os.getenv("ELASTIC_HOST")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
KNOWLEDGE_BASE_API_KEY = os.getenv("KNOWLEDGE_BASE_API_KEY")

SLACK_MCP_SERVER_URL="http://0.0.0.0:9001/sse"
TRANSCRIBE_MCP_SERVER_URL="http://127.0.0.1:9002/sse"
HRMS_MCP_SERVER_URL="http://0.0.0.0:9003/sse"
RESUME_PARSER_MCP_SERVER_URL="http://127.0.0.1:9004/sse"
PM_BOARD_MCP_URL="http://127.0.0.1:9005/sse"
ATS_MCP_SERVER_URL="http://127.0.0.1:9006/sse"
CALLING_MCP_SERVER_URL="http://127.0.0.1:9007/sse"
job_profile_agent_URL="http://127.0.0.1:9008/sse"
CANDIDATE_IATS_AGENT_URL="http://127.0.0.1:9009/sse"
CRM_FAQ_AGENT_URL="http://127.0.0.1:9010/sse"
CRM_LEAD_MCP_SERVER_URL="http://127.0.0.1:9011/sse"
CRM_EMAIL_MCP_SERVER_URL="http://127.0.0.1:9012/sse"
CRM_PIPELINE_MCP_SERVER_URL="http://127.0.0.1:9013/sse"
CRM_SALES_MCP_SERVER_URL="http://127.0.0.1:9014/sse"
CRM_INTELLIGENCE_MCP_SERVER_URL="http://127.0.0.1:9015/sse"
USER_MCP_SERVER_URL="http://127.0.0.1:9012/sse"
TRAVEL_EXPENSE_MCP_SERVER_URL="http://127.0.0.1:9020/sse"
ATTENDANCE_MCP_SERVER_URL="http://127.0.0.1:9020/sse"
PAYROLL_MCP_SERVER_URL="http://127.0.0.1:9020/sse"
RECRUITING_MCP_SERVER_URL="http://127.0.0.1:9020/sse"
REXNORD_MCP_SERVER_URL = ""

# GitHub MCP Server Configuration
# Uses official GitHub MCP server via stdio: @modelcontextprotocol/server-github
# No URL needed - communication via stdin/stdout

KNOWLEDGE_BASE_URL = "http://44.230.246.219/api"


ALLOWED_CALLING_EMAILS = [
    "priyank.gupta@w3villa.com",
    "ishank@w3villa.com",
    "priyank@w3villa.com",
    "rohit.kushwaha@w3villa.com",
    "bob@pspsolutions.net"
    # Add more authorized emails here
]

USER_PROJECT_URL = "api/v2/pm_board/projects/all"




