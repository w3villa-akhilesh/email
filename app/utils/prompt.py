import os
from app.utils.logger import logger
from app.services.email_notifier import send_exception_email

def read_prompt(filename):
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # goes from app/ to root/
    prompt_path = os.path.join(ROOT_DIR, 'prompts', filename)

    if not os.path.exists(prompt_path):
        logger.warning(f"Prompt file not found: {prompt_path}")
        send_exception_email("Error in read_prompt",f"Prompt file not found: {prompt_path}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path,'r') as file:
        instructions=file.read()
        return instructions


KIVO_AGENT_PROMPT=read_prompt("kivo_agent_prompt.txt")
HRMS_AGENT_PROMPT=read_prompt("hrms_agent_prompt.txt")
PMS_AGENT_PROMPT=read_prompt("pms_agent_prompt.txt")
NAME_SUGGESTION_AGENT_PROMPT=read_prompt("sub_agents/triage/name_suggestion_agent_prompt.txt")
TRANSCRIBE_AGENT_PROMPT=read_prompt("transcribe_agent_prompt.txt")
PM_BOARD_STORY_AGENT_PROMPT=read_prompt("pm_board_story_agent_prompt.txt")
LEAVE_AGENT_PROMPT=read_prompt("leave_agent_prompt.txt")
TRAVEL_EXPENSE_AGENT_PROMPT=read_prompt("travel_expense_agent_prompt.txt")
ATTENDANCE_AGENT_PROMPT=read_prompt("attendance_agent_prompt.txt")
PAYROLL_AGENT_PROMPT=read_prompt("payroll_agent_prompt.txt")
RECRUITING_AGENT_PROMPT=read_prompt("recruiting_agent_prompt.txt")
TRIAGE_AGENT_PROMPT=read_prompt("triage_agent_prompt.txt")
CRM_TRIAGE_AGENT_PROMPT=read_prompt("crm_triage_agent_prompt.txt")
CRM_EMAIL_AUTOMATION_AGENT_PROMPT=read_prompt("sub_agents/crm/crm_email_automation_agent_prompt.txt")
CRM_LEAD_MANAGEMENT_AGENT_PROMPT=read_prompt("sub_agents/crm/crm_lead_management_agent_prompt.txt")
CRM_PIPELINE_ANALYTICS_AGENT_PROMPT=read_prompt("sub_agents/crm/crm_pipeline_analytics_agent_prompt.txt")
CRM_SALES_AUTOMATION_AGENT_PROMPT=read_prompt("sub_agents/crm/crm_sales_automation_agent_prompt.txt")
CRM_CUSTOMER_INTELLIGENCE_AGENT_PROMPT=read_prompt("sub_agents/crm/crm_customer_intelligence_agent_prompt.txt")
KIVO_ATS_AGENT_PROMPT=read_prompt("ats_agent_prompt.txt")
RESUME_PARSER_PROMPT=read_prompt("resume_parser_prompt.txt")
CONTACT_EXTRACTION_PROMPT=read_prompt("contact_extraction_prompt.txt")
DEMO_RESUME_PARSER_PROMPT=read_prompt("demo_resume_parser_prompt.txt")
CALLING_AGENT_PROMPT=read_prompt("calling_agent_prompt.txt")
COMBINED_RESUME_AND_JOB_MATCHING_PROMPT =read_prompt("email_resume_vision_prompt.txt")
STORY_VALIDATION_INSTRUCTIONS=read_prompt("story_validation_instructions.txt")
CRM_FAQ_AGENT_PROMPT=read_prompt("crm_faq_agent_prompt.txt")
DATE_CALCULATION_RULES=read_prompt("date_calculation_rules.txt")
USER_AGENT_PROMPT=read_prompt("user_agent_prompt.txt")
HRMS_WORKFLOW_QUESTIONNAIRE_AGENT_PROMPT=read_prompt("sub_agents/hrms/hrms_questionnaire_workflow_agent_prompt.txt")
MODE_RULES=read_prompt("mode_rules.txt")
GREETING_INSTRUCTIONS=read_prompt("greeting_instructions.txt")

# IATS section -- START
IATS_AGENT_PROMPT=read_prompt("iats_agent_prompt.txt")
IATS_GLOBAL_INSTRUCTIONS=read_prompt("iats_global_instructions.txt")
job_profile_agent_PROMPT=read_prompt("sub_agents/iats/job_profile_agent_prompt.txt")
CANDIDATE_IATS_AGENT_PROMPT=read_prompt("sub_agents/iats/candidate_iats_agent_prompt.txt")
INTERVIEW_SCHEDULER_AGENT_PROMPT=read_prompt("sub_agents/iats/interview_scheduler_agent_prompt.txt")
OUTPUT_FORMATTER_AGENT_PROMPT=read_prompt("output_formatter_agent_prompt.txt")
HIRING_AGENT_PROMPT=read_prompt("sub_agents/iats/hiring_agent_prompt.txt")
CUSTOM_MATCHING_AGENT_PROMPT=read_prompt("sub_agents/iats/custom_matching_agent_prompt.txt")
JOB_PROFILE_MATCHING_AGENT_PROMPT=read_prompt("sub_agents/iats/job_profile_matching_agent_prompt.txt")
MATCHING_CRITERIA_AGENT_PROMPT=read_prompt("sub_agents/iats/matching_criteria_agent_prompt.txt")
SCORING_CRITERIA_AGENT_PROMPT=read_prompt("sub_agents/iats/scoring_criteria_agent_prompt.txt")
# IATS section -- END

# Performance Evaluation section -- START
METRICS_CALCULATION_AGENT_PROMPT = read_prompt("performance_evaluation/metrics_calculation_agent_prompt.txt")
SCORING_AGENT_PROMPT = read_prompt("performance_evaluation/scoring_agent_prompt.txt")
INSIGHT_ANALYSIS_AGENT_PROMPT = read_prompt("performance_evaluation/insight_analysis_agent_prompt.txt")
REPORT_GENERATION_AGENT_PROMPT = read_prompt("performance_evaluation/report_generation_agent_prompt.txt")
# Performance Evaluation section -- END

# Vision API section -- START
VISION_API_PROMPT = read_prompt("vision_agent_prompt.txt")
# Vision API section -- END

# CRM Analysis section -- START
CRM_ANALYSIS_AGENT_PROMPT = read_prompt("crm_analysis_agent_prompt.txt")
# CRM Analysis section -- END

# WhatsApp Button Formatter section -- START
WHATSAPP_BUTTON_FORMATTER_PROMPT = read_prompt("whatsapp_button_formatter_prompt.txt")
# WhatsApp Button Formatter section -- END  
