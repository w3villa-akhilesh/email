import os
from openai import OpenAI
from typing import Optional, Dict, Any, List, Union
from app.utils.logger import logger
from app.services.llm_engine import get_llm_engine, get_llm_credentials_based_on_company_id
from app.services.dynamic_prompt_factory import prompt_factory
from dotenv import load_dotenv
from app.services.redis_common_state import get_session_data
load_dotenv()
app_name="vision_agent"
async def handle_vision_api(data:dict,origin:str,company_id:str):
    logger.info(f"handle_vision_api: {data}")
    IMAGE_DETAIL_LEVEL = "high"

    try:        
        logger.info("vision_service is invoked")
        logger.info(f"app_name: {app_name}, company_id: {company_id}, origin: {origin}")
        model,api_key,base_url = get_llm_credentials_based_on_company_id(
            app_name="vision_agent",    
            company_id=company_id, 
            origin=origin
        )
        
        logger.info(f"llm_engine: {model},{api_key},{base_url}")
        client = OpenAI(api_key=api_key, base_url=base_url)

        image_url = data["image_url"]
        # Load vision prompt dynamically from prompt factory
        vision_prompt = prompt_factory.get_dynamic_prompt(
            agent_name="vision_agent",
            company_id=company_id
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": IMAGE_DETAIL_LEVEL
                            }
                        },
                    ],
                }
            ],
        )
        final_response = f"Note: This content was extracted from the uploaded image, remember this for future reference. \n\n{response.choices[0].message.content}"
        logger.info(f"response: {final_response}")
        return final_response
        
    except Exception as e:
        logger.error(f"Error in handle_vision_api: {str(e)}", exc_info=True)
        error_message = f"Sorry, I encountered an error while processing the image: {str(e)}. Please try uploading the image again or contact support if the issue persists."
        return error_message
