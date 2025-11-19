from typing import Dict, Any
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
from app.utils.final_logger import get_final_agent_response
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from app.services.lifecycle_hooks import (
    after_agent_invocation_callback_context, 
    before_agent_invocation_callback_context, 
    simple_after_tool_modifier, 
    simple_before_tool_modifier
)
from app.utils.logger import logger
from app.utils.prompt import (
    METRICS_CALCULATION_AGENT_PROMPT,
    SCORING_AGENT_PROMPT,
    INSIGHT_ANALYSIS_AGENT_PROMPT,
    REPORT_GENERATION_AGENT_PROMPT
)
from app.models.schema import (
    PerformanceScores,
    strict_generation_config,
    json_response_config
)
from app.helpers.performance_eval.common_utils import save_insight_analysis


async def create_performance_evaluation_sub_agents(model, performance_session_id, app_name) -> list:
    """Create the 4 sub-agents for the performance evaluation pipeline."""
    
    try:
        logger.info("Creating performance evaluation sub-agents")
        
        if not model:
            logger.error("Cannot create sub-agents: No model provided")
            return []
        
        agents = []
        
        # 1. Metrics Calculation Agent (starts with validated data from Pydantic)
        try:
            metrics_calculation_agent = LlmAgent(
                name="metrics_calculation_agent",
                model=model,
                instruction=METRICS_CALCULATION_AGENT_PROMPT,
                description="Computes core performance metrics from validated schema data",
                output_key="computed_metrics",
                before_agent_callback=before_agent_invocation_callback_context,
                after_agent_callback=after_agent_invocation_callback_context,
                before_tool_callback=simple_before_tool_modifier,
                after_tool_callback=simple_after_tool_modifier,
                generate_content_config=json_response_config
            )
            agents.append(metrics_calculation_agent)
            logger.info("Successfully created metrics calculation agent")
        except Exception as e:
            logger.error(f"Failed to create metrics calculation agent: {e}", exc_info=True)
            return []
        
        # 2. Scoring Agent
        try:
            scoring_agent = LlmAgent(
                name="scoring_agent",
                model=model,
                instruction=SCORING_AGENT_PROMPT,
                description="Applies weights and calculates overall performance score",
                output_key="performance_scores",
                output_schema=PerformanceScores,
                before_agent_callback=before_agent_invocation_callback_context,
                after_agent_callback=after_agent_invocation_callback_context,
                before_tool_callback=simple_before_tool_modifier,
                after_tool_callback=simple_after_tool_modifier,
                generate_content_config=json_response_config
            )
            agents.append(scoring_agent)
            logger.info("Successfully created scoring agent")
        except Exception as e:
            logger.error(f"Failed to create scoring agent: {e}", exc_info=True)
            return []
        
        # 3. Insight Analysis Agent
        try:


            async def before_insight_analysis(callback_context: CallbackContext):
                # First prune heavy raw datasets to avoid duplicate embedding
                
                await save_insight_analysis(callback_context, performance_session_id, app_name)
                return None
                    

            insight_analysis_agent = LlmAgent(
                name="insight_analysis_agent",
                model=model,
                instruction=INSIGHT_ANALYSIS_AGENT_PROMPT,
                description="Generates insights, trends, and automation recommendations",
                output_key="insights_and_trends",
                before_agent_callback=before_insight_analysis,
                after_agent_callback=after_agent_invocation_callback_context,
                before_tool_callback=simple_before_tool_modifier,
                after_tool_callback=simple_after_tool_modifier,
                generate_content_config=strict_generation_config
            )
            agents.append(insight_analysis_agent)
            logger.info("Successfully created insight analysis agent")
        except Exception as e:
            logger.error(f"Failed to create insight analysis agent: {e}", exc_info=True)
            return []
        
        # 4. Report Generation Agent
        try:
            report_generation_agent = LlmAgent(
                name="report_generation_agent",
                model=model,
                instruction=REPORT_GENERATION_AGENT_PROMPT,
                description="Creates comprehensive Markdown performance evaluation report",
                # No output_key - this is the final output
                before_agent_callback=before_agent_invocation_callback_context,
                after_agent_callback=after_agent_invocation_callback_context,
                before_tool_callback=simple_before_tool_modifier,
                after_tool_callback=simple_after_tool_modifier,
                generate_content_config=strict_generation_config
            )
            agents.append(report_generation_agent)
            logger.info("Successfully created report generation agent")
        except Exception as e:
            logger.error(f"Failed to create report generation agent: {e}", exc_info=True)
            return []
        
        logger.info(f"Successfully created all {len(agents)} performance evaluation sub-agents")
        return agents
        
    except Exception as e:
        logger.error(f"Error creating performance evaluation sub-agents: {e}", exc_info=True)
        return []


async def _execute_performance_pipeline(
    session_service,
    performance_session_id: str,
    user_id: str,
    app_name: str,
    company_id: str,
    origin: str,
    employee_id: str
) -> Dict[str, Any]:
    """Execute the performance evaluation pipeline."""
    
    try:
        # Get model configuration
        logger.info(f"Getting LLM engine for company: {company_id}, app: {app_name}, origin: {origin}")
        model = get_llm_engine('Triage_Agent', company_id, app_name, origin)
        
        if not model:
            logger.error(f"Failed to get LLM engine for company {company_id}")
            return {
                "success": False,
                "error": "LLM engine not available",
                "message": "Could not initialize language model"
            }
        
        # Create sub-agents
        logger.info("Creating performance evaluation sub-agents")
        sub_agents = await create_performance_evaluation_sub_agents(model, performance_session_id ,app_name)
        
        if not sub_agents or len(sub_agents) == 0:
            logger.error("Failed to create performance evaluation sub-agents")
            return {
                "success": False,
                "error": "Sub-agent creation failed",
                "message": "Could not create evaluation agents"
            }
        
        logger.info(f"Successfully created {len(sub_agents)} sub-agents: {[agent.name for agent in sub_agents]}")
        
        # Create sequential pipeline
        performance_pipeline = SequentialAgent(
            name="performance_evaluation_pipeline",
            sub_agents=sub_agents
        )
        
        # Create query content
        query_text = f"Generate comprehensive performance evaluation report for employee {employee_id}"
        content = types.Content(
            role='user', 
            parts=[types.Part(text=query_text)]
        )
        
        # Initialize Runner and execute the pipeline
        runner = Runner(
            agent=performance_pipeline,
            app_name=app_name,
            session_service=session_service
        )
        logger.info("Runner initialized. Starting performance evaluation pipeline execution.")
        
        # Execute the pipeline and get final response
        final_response, first_message_event_id, invocation_id = await get_final_agent_response(
            runner, user_id, performance_session_id, content
        )
        
        if not final_response:
            logger.error("Pipeline execution failed: No response received from agents")
            return {
                "success": False,
                "error": "Pipeline execution failed",
                "message": "No response received from evaluation pipeline"
            }
        
        logger.info(f"Performance evaluation pipeline completed successfully for employee {employee_id}")
        
        return {
            "success": True,
            "final_response": final_response,
            "first_message_event_id": first_message_event_id,
            "performance_pipeline": performance_pipeline,
            "sub_agents": sub_agents
        }
        
    except Exception as e:
        logger.error(f"Error executing performance pipeline for employee {employee_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to execute performance evaluation pipeline"
        }
