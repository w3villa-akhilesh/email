import os
import tempfile
import asyncio
import time
import httpx

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import AsyncOpenAI

from app.services.llm_engine import get_llm_credentials_based_on_company_id
from app.utils.logger import logger

load_dotenv()


async def async_download_and_transcribe(s3_url: str, company_id: str, app_name: str, origin: str) -> str:
    """
    Async variant: streams S3 download and uses AsyncOpenAI for Whisper.
    Logs download size/duration and transcription duration.
    Note: Always uses 'transcribe_agent' internally for getting LLM credentials,
    regardless of the app_name parameter passed.
    
    Args:
        s3_url: S3 URL of the audio file to transcribe
        company_id: Company identifier for credentials lookup
        app_name: Application name (kept for compatibility, not used for credentials)
        origin: Origin URL for credentials scoping
        
    Returns:
        Transcribed text string
    """
    temp_file_path = None
    try:
        logger.info(f"Downloading audio from S3 (async): {s3_url}")

        # Always use 'transcription_agent' for getting LLM credentials (not the passed app_name)
        model, api_key, llm_base_url = get_llm_credentials_based_on_company_id(
            app_name="transcription_agent", 
            company_id=company_id, 
            origin=origin
        )

        # Download the audio via async streaming
        start_download = time.perf_counter()
        size_header = None
        # httpx requires either a default or all four timeouts
        timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", s3_url) as resp:
                resp.raise_for_status()

                content_type = resp.headers.get("Content-Type", "")
                if content_type and not content_type.startswith("audio/"):
                    raise Exception(
                        f"Unsupported audio format: {content_type}. Only audio/* content is allowed."
                    )

                size_header = resp.headers.get("Content-Length")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                    async for chunk in resp.aiter_bytes(1024 * 1024):  # 1MB chunks
                        if chunk:
                            temp_file.write(chunk)
                    temp_file_path = temp_file.name
        download_duration = time.perf_counter() - start_download

        # Determine file size
        if size_header and size_header.isdigit():
            size_bytes = int(size_header)
        else:
            size_bytes = os.path.getsize(temp_file_path)
        size_mb = size_bytes / (1024 * 1024)
        logger.info(
            f"File saved temporarily at {temp_file_path} | size: {size_bytes} bytes ({size_mb:.2f} MB) | download: {download_duration:.2f}s"
        )

        # Transcribe using AsyncOpenAI
        logger.info("Sending audio to OpenAI Whisper model (async)...")
        start_transcription = time.perf_counter()
        client = AsyncOpenAI(api_key=api_key)
        with open(temp_file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model=model,
                file=audio_file,
            )
        transcription_duration = time.perf_counter() - start_transcription
        transcription_text = transcription.text
        logger.info(
            f"Transcription complete in {transcription_duration:.2f}s. Length: {len(transcription_text)} characters"
        )

        return transcription_text

    except Exception as e:
        logger.error(f"[ERROR] {str(e)}", exc_info=True)
        raise

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file deleted: {temp_file_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete temporary file: {cleanup_err}")


async def extract_query_from_voice_note(s3_url: str, company_id: str, origin: str, app_name:str) -> str:
    """
    Transcribe a voice note from an S3 URL using OpenAI Whisper via our
    `download_and_transcribe` service. Runs in a worker thread to avoid
    blocking the event loop.

    Args:
        s3_url: Pre-signed/public S3 URL to the audio file
        company_id: Company context to load the correct LLM credentials
        origin: Origin URL used for credentials scoping

    Returns:
        Transcribed text string
    """
    try:
        # Call async variant directly to avoid blocking the event loop
        text = await async_download_and_transcribe(
            s3_url=s3_url,
            company_id=company_id,
            app_name=app_name,
            origin=origin,
        )
        text = (text or "").strip()
        if not text:
            raise ValueError("Empty transcription")
        return text
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to transcribe voice note")


def voice_note_formatted_query(query:str):
    return f"This is the query received from a voice note and you need to process it. Query is {query}"
