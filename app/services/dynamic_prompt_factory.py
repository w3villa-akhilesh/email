import os
import re
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from app.services.agent_registry import AgentRegistryService
from app.utils.logger import logger

class DynamicPromptFactory:
    """
    Factory for creating dynamic prompts with agent availability checking
    and dynamic agent references
    """
    
    def __init__(self):
        self.prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        self._prompt_cache = {}
        self._available_prompts = None  # Cache for available prompt files
    
    def _find_prompt_file(self, prompt_file: str) -> Optional[str]:
        """Find prompt file in prompts directory and subdirectories"""
        # First try direct path
        direct_path = os.path.join(self.prompts_dir, prompt_file)
        if os.path.exists(direct_path):
            return direct_path
        
        # Search recursively in subdirectories
        for root, dirs, files in os.walk(self.prompts_dir):
            if prompt_file in files:
                return os.path.join(root, prompt_file)
        
        return None
    
    def _load_prompt_template(self, prompt_file: str) -> str:
        """Load prompt template from file with recursive search"""
        
        # Find the prompt file
        prompt_path = self._find_prompt_file(prompt_file)
        
        if not prompt_path:
            logger.error(f"Prompt file not found: {prompt_file}")
            return ""
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._prompt_cache[prompt_path] = content
                return content
        except Exception as e:
            logger.error(f"Error loading prompt file {prompt_path}: {e}")
            return ""
    
    def _get_hierarchical_agents_for_agent(self, agent_name: str, company_id: int) -> Dict[str, List[str]]:
        """Get hierarchical agents (parents and children) for a specific agent"""
        try:
            # Get child agents
            child_agents = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, agent_name)
            
            # Get parent agent
            parent_agents = self._get_parent_agent_for_company(agent_name, company_id)
            
            return {
                'children': child_agents,
                'parents': parent_agents
            }
        except Exception as e:
            logger.error(f"Error getting hierarchical agents for {agent_name}: {e}")
            return {'children': [], 'parents': []}
    
    def _get_parent_agent_for_company(self, agent_name: str, company_id: int) -> List[str]:
        """Get parent agent name for a specific agent and company"""
        try:
            from app.services.my_sql_client import get_db
            
            db = next(get_db())
            try:
                # Get the agent and its parent
                result = db.execute(text("""
                    SELECT parent.name
                    FROM agents child
                    JOIN agents parent ON child.parent_agent_id = parent.id
                    JOIN agent_mappings am ON parent.id = am.agent_id
                    WHERE child.name = :agent_name
                    AND am.company_id = :company_id
                    AND am.is_active = TRUE
                    AND parent.is_active = TRUE
                    AND child.is_active = TRUE
                """), {
                    'agent_name': agent_name,
                    'company_id': company_id
                })
                
                parent_row = result.fetchone()
                return [parent_row[0]] if parent_row else []
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting parent agent for {agent_name}: {e}")
            return []
    
    def _generate_handover_guidelines(self, hierarchical_agents: Dict[str, List[str]]) -> str:
        """Generate dynamic handover guidelines based on hierarchical agents"""
        
        guidelines = []
        
        # Agent capabilities mapping
        agent_capabilities = {
                                "triage_agent": "Routes and delegates employee queries to appropriate specialized agents based on query intent and context",
                                "user_agent": "Main user-facing agent that handles direct user interactions — including leave management, project stories, personal queries, and seamless routing to specialized user services",
                                "hrms_agent": "An HRMS Agent that efficiently handles all employee and organizational queries — including leave management, attendance tracking, employee details, holidays, events, worklogs, and project or reporting hierarchy information.", 
                                "calling_agent": "Handles call-related queries including initiating phone calls by employee name or direct phone number with internal HRMS lookup",   
                                "pm_board_story_agent": "Manages story creation and workflow in project management boards — including story validation, project assignment, and story movement between sprints",   
                                "pms_agent": "Handles performance evaluation queries — including employee performance evaluations, reviews, goal tracking, and comprehensive performance analysis",    
                                "leave_agent": "A Leave Agent that efficiently handles all leave-related queries — including applying for leave, get leave balance, checking leave details, and identifying employees who are on leave",    
                                "crm_faq_agent": "Handles CRM FAQ queries using knowledge base retrieval for customer relationship management questions",    
                                "crm_triage_agent": "Routes CRM-specific queries to appropriate CRM sub-agents for specialized customer relationship management",   
                                "crm_analysis_agent": "Generates professional email content for CRM communications based on multimodal messages (text, audio, images) for different purposes like reminders, greetings, follow-ups, and general outreach",
                                "iats_agent": "Main recruitment agent handling job and candidate queries, recruitment and talent acquisition workflows",   
                                "candidate_iats_agent": "Handles candidate queries, skills assessment, profiles, resume URLs, and job suitability evaluation",   
                                "job_profile_agent": "Manages job postings, job profiles, and hiring requirement specifications",    
                                "custom_matching_agent": "Handles custom matching workflows, candidate filtering, and advanced matching criteria configuration",    
                                "hiring_agent": "Manages hiring workflow queries, candidate stage updates, interview scheduling, and job offers",    
                                "job_profile_matching_agent": "Handles job profile matching workflows using criteria from selected job profiles",    
                                "interview_scheduler_agent": "Manages interview scheduling, calendar coordination, and interview workflow automation",    
                                "matching_criteria_agent": "Extracts and processes matching criteria from job profiles for candidate evaluation",
                                "scoring_criteria_agent": "Defines and manages scoring criteria for candidate evaluation and ranking systems",
                                "transcribe_agent": "Handles audio transcription, summarization, lead classification, and CRM integration for call recordings",
                                "user_leave_agent": "Manages user leave operations — including applications, balance inquiries, history, team status, and approvals",
                                "user_pm_board_story_agent": "Manages project board stories — including creation, validation, sprint assignment, and workflow automation",
                            }
        
        # Add parent agents
        if hierarchical_agents.get('parents'):
            guidelines.append("**Parent Agents:**")
            for parent in hierarchical_agents['parents']:
                capability = agent_capabilities.get(parent, "general operations")
                guidelines.append(f"- {parent}: {capability}")
        
        # Add child agents
        if hierarchical_agents.get('children'):
            guidelines.append("**Child Agents:**")
            for child in hierarchical_agents['children']:
                capability = agent_capabilities.get(child, "specialized operations")
                guidelines.append(f"- {child}: {capability}")
        
        if not guidelines:
            guidelines.append("- Handle queries within current agent context.")
        
        return "\n".join(guidelines)
    
    def _replace_dynamic_placeholders(self, prompt_content: str, agent_name: str, company_id: int) -> str:
        """Replace dynamic placeholders in prompt content"""
        
        # Replace handover guidelines with hierarchical agents
        if '<HANDOVER GUIDELINES>' in prompt_content:
            hierarchical_agents = self._get_hierarchical_agents_for_agent(agent_name, company_id)
            handover_guidelines = self._generate_handover_guidelines(hierarchical_agents)
            prompt_content = re.sub(
                r'<HANDOVER GUIDELINES>.*?</HANDOVER GUIDELINES>',
                f'<HANDOVER GUIDELINES>\n{handover_guidelines}\n</HANDOVER GUIDELINES>',
                prompt_content,
                flags=re.DOTALL
            )
        
        return prompt_content
    
    def _get_prompt_file_candidates(self, agent_name: str) -> List[str]:
        """Get list of potential prompt file names for an agent"""
        candidates = [
            f"{agent_name}_prompt.txt",
            f"{agent_name}.txt",
        ]
        
        # Add sub-agent specific paths based on agent naming patterns
        if "rexnord" in agent_name.lower() or agent_name in ["dealer_agent", "product_agent", "product_details_agent", "contact_rexnord_agent", "faq_agent"]:
            candidates.extend([
                f"rexnord/{agent_name}_prompt.txt",
                f"rexnord/{agent_name}.txt"
            ])
        elif "iats" in agent_name.lower():
            candidates.extend([
                f"sub_agents/iats/{agent_name}_prompt.txt",
                f"iats/{agent_name}_prompt.txt"
            ])
        elif "crm" in agent_name.lower():
            candidates.extend([
                f"sub_agents/crm/{agent_name}_prompt.txt",
                f"crm/{agent_name}_prompt.txt"
            ])
        elif "hrms" in agent_name.lower():
            candidates.extend([
                f"sub_agents/hrms/{agent_name}_prompt.txt",
                f"hrms/{agent_name}_prompt.txt"
            ])
        elif "triage" in agent_name.lower() or agent_name == "name_suggestion_agent":
            candidates.extend([
                f"sub_agents/triage/{agent_name}_prompt.txt",
                f"triage/{agent_name}_prompt.txt"
            ])
        elif any(perf_keyword in agent_name.lower() for perf_keyword in ["scoring", "metrics", "insight", "report"]):
            candidates.extend([
                f"performance_evaluation/{agent_name}_prompt.txt"
            ])
        
        return candidates

    def get_dynamic_prompt(
        self, 
        agent_name: str, 
        company_id: int = None,
        **template_vars
    ) -> str:
        """
        Get dynamic prompt for an agent with company-specific agent availability
        
        Args:
            agent_name: Name of the agent requesting the prompt
            company_id: Company ID to check agent availability
            **template_vars: Variables to substitute in the prompt template
        
        Returns:
            Dynamic prompt string with agent availability considered
        """
        
        # Get potential prompt file candidates
        prompt_candidates = self._get_prompt_file_candidates(agent_name)
        
        # Try to load prompt template from candidates
        prompt_template = ""
        for candidate in prompt_candidates:
            prompt_template = self._load_prompt_template(candidate)
            if prompt_template:
                logger.debug(f"Found prompt template for {agent_name} at: {candidate}")
                break
        
        if not prompt_template:
            logger.warning(f"No prompt template found for {agent_name} in any location, using fallback")
            prompt_template = self._get_fallback_prompt(agent_name)
        
        # Replace dynamic placeholders with hierarchical agents
        dynamic_prompt = self._replace_dynamic_placeholders(prompt_template, agent_name, company_id)
        
        # Get hierarchical agents for template variables
        hierarchical_agents = self._get_hierarchical_agents_for_agent(agent_name, company_id)
        template_vars['hierarchical_agents'] = hierarchical_agents
        template_vars['child_agents'] = hierarchical_agents.get('children', [])
        template_vars['parent_agents'] = hierarchical_agents.get('parents', [])
        
        # Format the prompt with provided variables
        try:
            formatted_prompt = dynamic_prompt.format(**template_vars)
            return formatted_prompt
        except KeyError as e:
            logger.warning(f"Missing template variable {e} for {agent_name} prompt")
            return dynamic_prompt
        except Exception as e:
            logger.error(f"Error formatting prompt for {agent_name}: {e}")
            return dynamic_prompt
    
    def _get_fallback_prompt(self, agent_name: str) -> str:
        """Get fallback prompt if specific prompt file not found"""
        return f"""You are {agent_name}, a professional AI assistant.

        Your responsibilities include handling user queries professionally and efficiently.

        <HANDOVER GUIDELINES>
        - Handle queries within current agent context.
        </HANDOVER GUIDELINES>

        Guidelines:
        1. Handle user queries within your capabilities
        2. If you need to transfer to another agent, only use agents from the hierarchical list
        3. Be professional and helpful in all interactions
        4. Never mention internal routing or technical details to users

        Communication should be clear, concise, and user-focused.
        """
    
    def get_agent_description(self, agent_name: str, company_id: int = None) -> str:
        """Get dynamic agent description based on hierarchical agents"""
        
        hierarchical_agents = self._get_hierarchical_agents_for_agent(agent_name, company_id)
        
        # Base descriptions
        all_related_agents = hierarchical_agents.get('parents', []) + hierarchical_agents.get('children', [])
        descriptions = {
            "triage_agent": f"Routes queries to appropriate specialized agents. Related agents: {', '.join(all_related_agents) if all_related_agents else 'none'}",
            "hrms_agent": "Handles HR operations, employee information, and workplace queries",
            "calling_agent": "Manages call-related queries and phone operations",
            "pm_board_story_agent": "Handles project management and story creation",
            "pms_agent": "Manages performance evaluation and reviews",
            "leave_agent": "Handles leave applications and leave management",
            "crm_faq_agent": "Handles CRM-related FAQ queries by retrieving relevant information from a FAISS-based knowledge base and generating context-aware responses",
            "crm_triage_agent": f"Routes CRM queries to appropriate specialized CRM sub-agents. Child agents: {', '.join(hierarchical_agents.get('children', []))}",
            "crm_analysis_agent": "Generates professional email content for CRM communications based on multimodal messages for various purposes",
            "iats_agent": f"Handles job and candidate queries, recruitment and talent acquisition. Child agents: {', '.join(hierarchical_agents.get('children', []))}",
            "candidate_iats_agent": "Handles queries related to candidates, their skills, profiles, resume URLs, and suitability for jobs",
            "job_profile_agent": "Handles queries related to job postings, job profiles, and hiring operations",
            "custom_matching_agent": "Handles the entire workflow for custom matching job applicants, including gathering criteria, finding candidates, and running matching jobs",
            "matching_criteria_agent": "Takes gathered matching criteria, formats and processes it for matching operations",
            "scoring_criteria_agent": "Takes gathered scoring criteria, formats and processes it for scoring operations",
            "interview_scheduler_agent": "Manages interview scheduling by collecting interview details, confirming with users, and scheduling interviews",
            "hiring_agent": "Handles hiring workflow queries such as candidate stage updates, interview scheduling, and offers",
            "job_profile_matching_agent": "Handles matching workflows using criteria from selected job profiles",
            "transcribe_agent": "Handles audio transcription, call summarization, lead classification, and automated CRM integration",
            "travel_expense_agent": "Handles travel expense management queries including travel requests, expense reports, travel policies, reimbursements, travel bookings, expense approvals, and travel budget management",
            "attendance_agent": "Handles attendance and leave management queries including attendance summary, leave requests, absent employees, late arrivals, leave approvals, attendance reports, and punctuality analysis",
            "payroll_agent": "Handles payroll management and employee compensation queries including salary summaries, pending payments, deductions analysis, payroll reports, expense tracking, and compensation analytics",
            "recruiting_agent": "Handles recruitment and talent acquisition queries including open positions, candidate pipeline, interview tracking, hiring analytics, job offers, recruitment metrics, and talent sourcing",
            "hrms_questionnaire_workflow_agent": "Guides users through HRMS workflows via brief questionnaires, then returns clear, role-aware step-by-step procedures (e.g., add employee, onboard, offboard)",
            "name_suggestion_agent": "Handles queries to find and suggest employee names similar to a given input using semantic search with contextual information",
            # Rexnord agents
            "rexnord_triage_agent": f"Routes Rexnord customer queries to specialized agents for products, dealers, contact info, and FAQs. Child agents: {', '.join(hierarchical_agents.get('children', []))}",
            "dealer_agent": "Helps users find and connect with authorized Rexnord dealers by state/region, providing dealer contact information",
            "product_agent": f"Assists with Rexnord product information, catalogs, specifications, and product selection. Child agents: {', '.join(hierarchical_agents.get('children', []))}",
            "product_details_agent": "Provides detailed specifications, catalogs, images, and documentation for specific Rexnord products",
            "contact_rexnord_agent": "Handles queries about contacting Rexnord directly for purchases, support, and general inquiries",
            "faq_agent": "Answers frequently asked questions about Rexnord products, services, policies, warranty, and company information",
        }
        
        description = descriptions.get(agent_name)
        if description is None:
            # Agent not found in descriptions
            return f"Agent {agent_name} handles specialized operations. Related agents: {', '.join(all_related_agents) if all_related_agents else 'none'}"
        
        return description
    
    def validate_agent_transfer(self, from_agent: str, to_agent: str, company_id: int = None) -> Dict[str, Any]:
        """
        Validate if agent transfer is possible based on hierarchical relationships
        
        Returns:
            {
                'valid': bool,
                'message': str,
                'suggested_agent': str or None,
                'hierarchical_agents': Dict[str, List[str]]
            }
        """
        
        hierarchical_agents = self._get_hierarchical_agents_for_agent(from_agent, company_id)
        all_related_agents = hierarchical_agents.get('parents', []) + hierarchical_agents.get('children', [])
        
        if to_agent in all_related_agents:
            return {
                'valid': True,
                'message': f"Transfer to {to_agent} is valid (hierarchically related)",
                'suggested_agent': to_agent,
                'hierarchical_agents': hierarchical_agents
            }
        
        # Suggest from hierarchical agents or fallback to hrms_agent
        suggested_agent = all_related_agents[0] if all_related_agents else 'hrms_agent'
        
        return {
            'valid': False,
            'message': f"Agent {to_agent} is not in the hierarchical chain of {from_agent}. Suggested alternative: {suggested_agent}",
            'suggested_agent': suggested_agent,
            'hierarchical_agents': hierarchical_agents
        }
    
    def get_available_prompt_files(self) -> Dict[str, str]:
        """Get all available prompt files with their relative paths"""
        if self._available_prompts is not None:
            return self._available_prompts
        
        available_prompts = {}
        
        for root, dirs, files in os.walk(self.prompts_dir):
            for file in files:
                if file.endswith('.txt'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.prompts_dir)
                    # Extract agent name from filename
                    agent_name = file.replace('_prompt.txt', '').replace('.txt', '')
                    available_prompts[agent_name] = relative_path
        
        self._available_prompts = available_prompts
        return available_prompts
    
    def list_prompt_files_by_category(self) -> Dict[str, List[str]]:
        """List prompt files organized by category/subdirectory"""
        categories = {
            'root': [],
            'sub_agents_iats': [],
            'sub_agents_crm': [],
            'sub_agents_hrms': [],
            'sub_agents_triage': [],
            'performance_evaluation': [],
            'other': []
        }
        
        available_prompts = self.get_available_prompt_files()
        
        for agent_name, relative_path in available_prompts.items():
            if relative_path.startswith('sub_agents/iats/'):
                categories['sub_agents_iats'].append(agent_name)
            elif relative_path.startswith('sub_agents/crm/'):
                categories['sub_agents_crm'].append(agent_name)
            elif relative_path.startswith('sub_agents/hrms/'):
                categories['sub_agents_hrms'].append(agent_name)
            elif relative_path.startswith('sub_agents/triage/'):
                categories['sub_agents_triage'].append(agent_name)
            elif relative_path.startswith('performance_evaluation/'):
                categories['performance_evaluation'].append(agent_name)
            elif '/' not in relative_path:
                categories['root'].append(agent_name)
            else:
                categories['other'].append(agent_name)
        
        return categories
    
    def clear_cache(self):
        """Clear the prompt cache and available prompts cache"""
        self._prompt_cache.clear()
        self._available_prompts = None
        logger.info("Prompt cache cleared")

# Global instance
prompt_factory = DynamicPromptFactory()
