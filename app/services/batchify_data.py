from app.utils.logger import logger
from app.helpers.pm_board_agent import initiate_pm_board_agent 
from app.services.redis_common_state import save_session_data, delete_session_data


def batchify(data_list, batch_size):
    for i in range(0, len(data_list), batch_size):
        yield data_list[i:i + batch_size]

async def process_story_individually(story_data, ka_session_id, ka_user_id, company_id, app_name, origin, project_instructions, project_id):
    """
    Process each story individually.
    """
    all_results = {}
    save_session_data(ka_session_id, {"project_id": project_id})
    for i, story in enumerate(story_data):
        story_session_id = f"{ka_session_id}_story{i+1}"
        logger.info(f"Processing story {i+1}/{len(story_data)} with session ID {story_session_id}")

        result = await initiate_pm_board_agent(
            project_instructions, [story], story_session_id, ka_user_id, company_id, app_name, origin
        )

        all_results[story_session_id] = {
            "story_number": i + 1,
            "result": result
        }
    return all_results


async def process_story_in_batches(story_batches, ka_session_id, ka_user_id, company_id, app_name, origin, project_instructions):
    """
    Process stories in batches.
    """
    all_results = {}
    for i, batch in enumerate(story_batches):
        batch_session_id = f"{ka_session_id}_batch{i+1}"
        logger.info(f"Processing batch {i+1}/{len(story_batches)} with session ID {batch_session_id}")

        result = await initiate_pm_board_agent(
            project_instructions, batch, batch_session_id, ka_user_id, company_id, app_name, origin
        )

        all_results[batch_session_id] = {
            "batch_number": i + 1,
            "batch_size": len(batch),
            "result": result
        }
    return all_results
