import os
import requests
import logging
import tempfile
import uuid
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict, Any
from openai import OpenAI
import json
from app.services.my_sql_client import get_engine
from sqlalchemy.orm import Session
from app.models.db_models import EmailInboxConfig
from app.utils.logger import logger
import re
import base64
from app.models.db_models import LLMCredentials
from cryptography.fernet import Fernet
from pydantic import BaseModel
# Load environment variables
load_dotenv()

class ResponseFormat(BaseModel):
    """Response model for job application classification and matching."""
    intent: str  # "true" or "false" - whether the email is about job seeking
    best_matched_job_id: str  # job ID or "NONE" if no match found

# Content type constants
SUPPORTED_CONTENT_TYPES = [
    "application/pdf",
    "application/msword",  # DOC
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # DOCX
]

CONTENT_TYPE_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
}

DEFAULT_FILE_EXTENSION = ".pdf"

def decrypt_text(ciphertext: str) -> str:
    try:
        FERNET_KEY = os.getenv("LLM_ENCRYPTION_KEY")
        if not FERNET_KEY:
            raise ValueError("Encryption key not found in environment variables.")
        fernet = Fernet(FERNET_KEY)
        return fernet.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""  # Return an empty string or handle as needed

def _get_company_config(email_id: str) -> Optional[dict]:
    logger.info(f"Fetching company config for email: {email_id}")
    try:
        engine = get_engine()
        with Session(engine) as session:
            # Add logging to check the query results
            logger.info(f"Querying EmailInboxConfig for email: {email_id}")
            cfg = (
                session.query(EmailInboxConfig)
                .filter(EmailInboxConfig.account_email == str(email_id))
                .first()
            )
            # Ensure the email address matches the database entry exactly
            if not cfg:
                logger.error(f"No configuration found for email: {email_id}")
                return None

            return {
                "resume_parser_access_token": cfg.resume_parser_access_token,
                "domain": cfg.domain,
                "company_id": cfg.company_id,
                "account_email": cfg.account_email,
                "llm_api_key": decrypt_text(cfg.llm_key),
                "llm_api_base_url": cfg.llm_base_url
            }
    except Exception as e:
        logger.error(f"DB error fetching company config: {e}")
        return None

def classify_and_infer_job_profile(subject: str, body: str, jobs: List[Dict[str, Any]], email_infox_cfg: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
    if not jobs:
        return False, None
    try:
        titles = [j.get("title") or j.get("name") or "" for j in jobs]
        id_map = { (j.get("title") or j.get("name") or "").strip(): str(j.get("id")) for j in jobs }
        
        # Update the prompt to include job IDs
        prompt = (
            "You are a classifier and job profile matcher.\n"
            "Step 1 — Determine if the email is about applying for a job, finding a job, or expressing interest in job opportunities. "
            "This includes any wording that indicates the sender is seeking employment, applying for a role, or asking to be considered for work. "
            "Be inclusive — even short or vague expressions like 'looking for new job opportunities' or 'seeking opportunities' should be classified as job-seeking. "
            "If the email does not express job-seeking intent, return 'false'.\n\n"
            "Step 2 — From the provided job titles and IDs, select the single best match for the candidate based on the email's subject and body. "
            "If no clear match is found, return 'NONE'.\n\n"
            "Output format: Return only a JSON object with the following structure: {\"intent\": \"true\" or \"false\", \"best_matched_job_id\": job ID or \"NONE\"}.\n\n"
            f"Job Titles and IDs: {json.dumps([{ 'id': j.get('id'), 'title': j.get('job_title') } for j in jobs])}\n\n"
            f"Email Subject: {subject or ''}\n"
            f"Email Body: {body or ''}"
        )

        logger.info(f"Prompt --->>: {prompt}")
        DEFAULT_MODEL = "gpt-4o-mini"
        try:
            client = OpenAI(
                api_key=email_infox_cfg.get('llm_api_key'), 
                base_url=email_infox_cfg.get('llm_api_base_url')
            )
            
            completion = client.responses.parse(
                model=DEFAULT_MODEL,
                input=[
                    {"role": "system", "content": prompt},
                ],
                text_format=ResponseFormat,
            )
            
            final_response = completion.output_parsed
            logger.info(f"Structured output completion")

            intent = final_response.intent
            best_matched_job_id = final_response.best_matched_job_id
            logger.info(f"Intent: {intent}")
            logger.info(f"Best matched job id: {best_matched_job_id}")

            # Convert to expected format
            is_job_application = intent.lower() == 'true'
            job_profile_id = best_matched_job_id if best_matched_job_id != "NONE" else None
            
            logger.info(f"Final processing result - is_job_application: {is_job_application}, job_profile_id: {job_profile_id}")
            return is_job_application, job_profile_id
            
        except Exception as structured_error:
            logger.error(f"Structured output parsing failed: {structured_error}")
            # Fallback: try to parse manually if structured output fails
            try:
                logger.info("Attempting fallback to manual parsing...")
                # You can add fallback logic here if needed
                return False, None
            except Exception as fallback_error:
                logger.error(f"Fallback parsing also failed: {fallback_error}")
                return False, None
    except Exception as e:
        logger.warning(f"Classification and inference failed, defaulting to False and None: {e}")
        return False, None

def _fetch_active_job_profiles(ats_base_url: str, company_id: str, access_token: str) -> List[Dict[str, Any]]:
    try:
        url = f"{ats_base_url.rstrip('/')}/api/v1/active_jds"
        params = {"company_id": company_id, "resume_parser_access_token": access_token}
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            if isinstance(data, list):
                return data
        logger.error(f"Active JD fetch failed: {resp.status_code} {resp.text}")
        return []
    except Exception as e:
        logger.error(f"Error fetching active job profiles: {e}")
        return []

def forward_to_resume_parser(email_content, email_body, attachments, company_id: Optional[str] = None):
    """
    Forward the email content to the resume parser API.
    
    Args:
        email_content (dict): Dictionary containing email metadata (subject, from, to, date)
        email_body (str): The body content of the email
        attachments (list): List of dictionaries containing attachment information
        
    Returns:
        bool: True if forwarding was successful, False otherwise
    """
    logger.info("Starting to forward email to resume parser")
    try:
        # Find all supported document attachments (PDF, DOC, DOCX)
        supported_attachments = []
        for att in attachments:
            if att["content_type"] in SUPPORTED_CONTENT_TYPES:
                supported_attachments.append(att)
                logger.debug(f"Found supported document attachment: {att['filename']} (type: {att['content_type']})")

        if not supported_attachments:
            logger.error("No supported document attachment (PDF, DOC, DOCX) found in the email")
            return False
        
        logger.info(f"Found {len(supported_attachments)} supported document(s) to process")

        # Extract the email address from the 'To' field
        monitoring_email_match = re.search(r'<(.+?)>', email_content.get("to"))
        monitoring_email = monitoring_email_match.group(1) if monitoring_email_match else email_content.get("to")

        # Use the extracted monitoring email to fetch the company config
        email_infox_cfg = _get_company_config(monitoring_email) if monitoring_email else None

        domain = (email_infox_cfg or {}).get("domain")
        resume_parser_access_token = (email_infox_cfg or {}).get("resume_parser_access_token")
        
        logger.info(f"Domain --- >>>>: {domain}")
        logger.info(f"Resume parser access token: {resume_parser_access_token}")
        
        # Get job profiles and check intent once for the email
        jobs = _fetch_active_job_profiles(domain, company_id, resume_parser_access_token)
        is_job_application, job_profile_id = classify_and_infer_job_profile(email_content.get("subject"), email_body, jobs, email_infox_cfg)

        if not is_job_application:
            logger.info("Email skipped: not detected as a job application.")
            return False

        # Process each supported attachment separately
        successful_submissions = 0
        total_attachments = len(supported_attachments)
        
        for i, document_attachment in enumerate(supported_attachments, 1):
            logger.info(f"Processing attachment {i}/{total_attachments}: {document_attachment['filename']}")
            
            try:
                # Create a temporary file to store the document
                # Determine the appropriate file extension based on content type
                content_type = document_attachment["content_type"]
                file_extension = CONTENT_TYPE_TO_EXTENSION.get(content_type, DEFAULT_FILE_EXTENSION)
                    
                document_filename = f"resume_{uuid.uuid4().hex}{file_extension}"
                document_path = os.path.join(tempfile.gettempdir(), document_filename)
                logger.debug(f"Temporary document file created at: {document_path}")

                # Save the document attachment to the temporary file
                with open(document_path, 'wb') as f:
                    f.write(document_attachment.get("content", b""))

                # Prepare the payload for the API endpoint
                data = {
                    "company_id": company_id,
                    "resume_parser_access_token": resume_parser_access_token,
                    "job_profile_id": job_profile_id
                }

                # Prepare files for this specific attachment
                files = {
                    "attachments[]": (document_attachment["filename"], document_attachment.get("content", b""), document_attachment["content_type"])
                }

                # Send the request to the API endpoint
                api_url = f"{domain}/api/v1/create_job_applicant_from_resume"
                logger.info(f"Sending request to create job applicant from resume API for: {document_attachment['filename']}")
                response = requests.post(api_url, data=data, files=files)

                if response.status_code == 200:
                    logger.info(f"Successfully processed attachment: {document_attachment['filename']}")
                    successful_submissions += 1
                else:
                    logger.error(f"Failed to process attachment {document_attachment['filename']}: {response.text}")
                
                # Clean up the temporary file
                try:
                    os.remove(document_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary document file {document_path}: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error processing attachment {document_attachment['filename']}: {str(e)}")
                # Clean up the temporary file if it exists
                if 'document_path' in locals():
                    try:
                        os.remove(document_path)
                    except Exception:
                        pass
        
        # Log the final results
        logger.info(f"Processing completed: {successful_submissions}/{total_attachments} attachments processed successfully")
        return successful_submissions > 0

    except Exception as e:
        logger.error(f"Error forwarding to resume parser: {str(e)}")
        return False 