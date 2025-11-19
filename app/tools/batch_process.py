import os
import json
import time
from fastapi import BackgroundTasks
from openai import OpenAI
import uuid
from app.models.db_models import CustomMatchingCriteria, CustomMatchingResultsApplicantData
from app.services.redis_common_state import get_session_data, save_session_data
from app.utils.logger import logger
import asyncio
from typing import List, Dict, Any
from app.services.my_sql_client import get_db
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url = os.getenv("OPENAI_API_BASE"))
# Initialize OpenAI client

# Helper functions
def create_jsonl_file(custom_matching_id: str, system_prompt: str, resumes: List[Any], model="gpt-4o-mini") -> str:
    # Ensure folder exists
    output_dir = "batch_inputs"
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, f"batch_input_{custom_matching_id}.jsonl")

    with open(filename, "w") as f:
        for idx, resume in enumerate(resumes):
            request = {
                "custom_id": f"req_{idx}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(resume)}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            }
            f.write(json.dumps(request) + "\n")

    logger.info(f"JSONL file created at: {filename}")
    return filename


async def upload_file(file_path: str) -> str:
    with open(file_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="batch")
    logger.info(f"Uploaded file. ID: {uploaded.id}")
    return uploaded.id


async def get_batch_request_count(batch_id):
    batch = client.batches.retrieve(batch_id)
    status = batch.status
    request_count = batch.request_counts
    complete_status = {"status":status, "request_count":request_count}
    logger.debug(f"fetching complete status for {complete_status}")
    return complete_status
    

async def submit_batch(session_id, custom_matching_id, file_id: str, endpoint="/v1/chat/completions", completion_window="24h") -> str:
    response = client.batches.create(
        input_file_id=file_id,
        endpoint=endpoint,
        completion_window=completion_window,
        metadata={"description": "Resume screening batch job"}
    )
    batch_id = response.id

    # as batch_id is retrieved save it to session for progress purpose.
    session_data = get_session_data(session_id)

    matching_status_key = f"match_status_{custom_matching_id}"
    match_status_data = {}
    if session_data.get(matching_status_key):
        try:
            match_status_data = json.loads(session_data[matching_status_key])
        except Exception:
            pass

    match_status_data["batch_id"] = batch_id

    session_data[matching_status_key] = json.dumps(match_status_data)
    save_session_data(session_id, session_data)

    logger.debug(f"saving batch_id in session: {match_status_data['batch_id']}")

    logger.info(f"Submitted batch job. ID: {batch_id}")
    return batch_id


async def wait_for_batch_completion(batch_id, poll_interval=15):
    """
    Polls the batch job status until completion and returns output_file_id.
    """
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        request_count = batch.request_counts
        logger.debug(f"Batch request count: {request_count}")
        logger.debug(f"Batch status: {status}")

        
        if status == "completed":
            logger.info("Batch completed.")
            return batch.output_file_id
        elif status in ["failed", "cancelled"]:
            raise Exception(f"Batch {status}. Check batch ID: {batch_id}")
        
        time.sleep(poll_interval)


# function first download the results, process them into appropiate format and then insert into database.
async def download_results(custom_matching_id:str, file_id: str) -> List[dict]:
    file_content = client.files.content(file_id)
    content = file_content.text
    logger.info("Downloaded batch result.")

    responses = []

    for line in content.strip().splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            content_str = item["response"]["body"]["choices"][0]["message"]["content"]
            parsed = json.loads(content_str)  # convert stringified JSON to dict
            responses.append(parsed)
        except Exception as e:
            logger.error(f"Error parsing line: {line[:100]}... => {e}")

    job_applicants = []
    for r in responses:  # response is a list of dicts
        job_applicants.extend(r.get("job_applicants", []))
    
    # inserting results of batch operation in database.
    logger.info("Initating insertion in database")
    await insert_matching_results_into_db(custom_matching_id, job_applicants)

    return job_applicants


async def insert_matching_results_into_db(custom_matching_id: int, job_applicants: list[dict]):
    db = next(get_db())
    try:
        logger.info("Successfully started insertion of matching results into database")
        entries = []
        for app in job_applicants:
            entries.append(CustomMatchingResultsApplicantData(
                custom_matching_id=custom_matching_id,
                applicant_id=str(app.get("job_applicant_id")),
                matching_score=str(app.get("job_matching_percentage")),
                matching_score_reasoning=app.get("job_matching_percentage_reason", "")
            ))
        

        db.add_all(entries)
        criteria_entry = db.query(CustomMatchingCriteria).filter_by(custom_matching_id=custom_matching_id).first()
        if criteria_entry:
            criteria_entry.matching_status = "completed"

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def process_batch(
    resumes: List[Dict],
    custom_matching_id: int,
    session_id: str,
    matching_criteria: dict,
    scoring_criteria: dict
    ) -> dict:
    """
    Modular function to run matching job using extracted resume data and scoring/matching criteria.

    Args:
        custom_matching_id (str): ID used to track batch — also used as tracking ID.
        session_id (str): Redis session ID to fetch applicant data.
        matching_criteria (dict): Keywords, required tags, etc.
        scoring_criteria (dict): How scoring is calculated.

    Returns:
        dict: Status of job submission.
    """
    
    # Step 3: Build system prompt
    system_prompt = f"""
    You are a resume matching assistant. You will get job_applicant_id and job_applicant_resume_extracted_text in input.
    Example of input:
    `
    {{
    "job_applicant_id": 102,
    "job_applicant_resume_extracted_text": "Skilled in JavaScript and frontend development. No experience in Python or Django."
    }} 
    `
    For each provided applicant's extracted resume data, use the given scoring criteria and matching keywords to calculate:
    - job_matching_percentage (float)
    - job_matching_percentage_reason (string explaining how the score was calculated, breaking down keywords, title, and profile).
    Provided scroing criteria is : {scoring_criteria}
    Provided matching critera is : {matching_criteria}

    Rules for output:
    1. Output needs to be *strictly* in provided format — no extra text before or after the JSON output.

    **Output JSON format:**
    {{
    "job_applicants": [
        {{
        "job_applicant_id": ...,
        "job_matching_percentage": ...,
        "job_matching_percentage_reason": "..."
        }},
        ...
    ]
    }}

    **Example Output:**

    {{
    "job_applicants": [
        {{
        "job_applicant_id": 1,
        "job_matching_percentage": 100,
        "job_matching_percentage_reason": "Matched all keywords (Python, Django, REST APIs), job title matched, and met both education and experience criteria. 60 + 20 + 20 = 100."
        }},
        {{
        "job_applicant_id": 2,
        "job_matching_percentage": 0,
        "job_matching_percentage_reason": "Did not meet experience criterion, job title mismatch, and did not match any backend-related keywords. 0 + 0 + 0 = 0."
        }},
        {{
        "job_applicant_id": 3,
        "job_matching_percentage": 46.7,
        "job_matching_percentage_reason": "Matched Python and REST APIs (but missing Django), partial profile match (missing education), job title partially matches. 40 + 6.7 + 0 = 46.7."
        }}
    ]
    }}
    """

    try:
        # Step 4: Process batch with OpenAI-style flow
        jsonl_path = create_jsonl_file(custom_matching_id, system_prompt=system_prompt, resumes=resumes)
        file_id = await upload_file(jsonl_path)
        real_batch_id = await submit_batch(session_id, custom_matching_id, file_id)
        output_file_id = await wait_for_batch_completion(real_batch_id)
        result = await download_results(custom_matching_id, output_file_id)

        
        job_applicants = result.get("job_applicants", [])
        if not job_applicants:
            raise ValueError("No job_applicants found in batch result")
        return {"status": "completed", "custom_matching_id": custom_matching_id}

    except Exception as e:

        return {"status": "error", "message": str(e)}
    