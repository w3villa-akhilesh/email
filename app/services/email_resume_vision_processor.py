import os
import json
import base64
import requests
import shutil
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
from app.utils.logger import logger
from app.utils.prompt import COMBINED_RESUME_AND_JOB_MATCHING_PROMPT

class EmailResumeVisionProcessor:
    def __init__(self):
        self.api_key = os.getenv("LLM_OPEN_API_KEY_VIR")
        self.api_url = f"{os.getenv('LLM_OPEN_API_BASE_VIR')}/chat/completions"
        self.active_jds_api_url = os.getenv("ACTIVE_JDS_API_URL")
        self.company_id = os.getenv("COMPANY_ID")
        self.resume_parser_access_token = os.getenv("RESUME_PARSER_ACCESS_TOKEN")
        self.max_image_size_mb = 5
        self.max_image_pixels = 600000
        self.supported_formats = ['PNG', 'JPEG']
        self.llm_model = "gpt-4o-mini"
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OpenAI API key not configured")
        logger.info("EmailResumeVisionProcessor initialized successfully")

    def _cleanup_image(self, image_path: str, session_id: str) -> None:
        """Clean up temporary image file after processing. Keep directory for concurrent sessions."""
        try:
            image_path = Path(image_path)
            if image_path.exists():
                os.remove(image_path)
                logger.info(f"[{session_id}] Cleaned up temporary image: {image_path}")
            else:
                logger.debug(f"[{session_id}] Image file not found for cleanup: {image_path}")
                
        except FileNotFoundError:
            logger.debug(f"[{session_id}] Image file not found during cleanup: {image_path}")
        except Exception as e:
            logger.warning(f"[{session_id}] Failed to delete temporary image {image_path}: {str(e)}")

    def _validate_image_size(self, image_path: str) -> tuple[bool, float]:
        try:
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            logger.info(f"Image size: {file_size_mb:.2f}MB")
            if file_size_mb > self.max_image_size_mb:
                logger.warning(f"Image size ({file_size_mb:.2f}MB) exceeds threshold of {self.max_image_size_mb}MB")
                return False, file_size_mb
            return True, file_size_mb
        except Exception as e:
            logger.error(f"Error validating image size: {str(e)}")
            raise

    def _resize_image(self, image: Image.Image, max_pixels: int = 600000) -> Image.Image:
        try:
            width, height = image.size
            total_pixels = width * height
            if total_pixels <= max_pixels:
                logger.info(f"Image resolution {width}x{height} is within limit")
                return image
            scale = (max_pixels / total_pixels) ** 0.5
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            raise

    def _compress_image(self, image: Image.Image, max_size_mb: float = 5) -> bytes:
        try:
            output = BytesIO()
            image = image.convert("L") # Convert to grayscale for smaller size
            quality = 70
            image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
            while output.getbuffer().nbytes / (1024 * 1024) > max_size_mb and quality > 10:
                output = BytesIO()
                quality -= 3
                image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
                logger.info(f"Compressing image with quality={quality}")
            final_size_mb = output.getbuffer().nbytes / (1024 * 1024)
            if final_size_mb > max_size_mb:
                raise ValueError(f"Could not compress image below {max_size_mb}MB (final size: {final_size_mb:.2f}MB)")
            logger.info(f"Compressed image size: {final_size_mb:.2f}MB")
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error compressing image: {str(e)}")
            raise

    def _get_llm_response(self, messages: list, response_format: dict = None) -> dict:
        """Helper to make LLM API calls."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3
        }
        if response_format:
            payload["response_format"] = response_format
        response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=180) # Increased timeout for combined task
        response.raise_for_status()
        return response.json()

    def _fetch_active_jd_keywords(self, session_id: str) -> dict:
        """Fetches active job keywords from the specified API."""
        try:
            params = {
                "company_id": self.company_id,
                "resume_parser_access_token": self.resume_parser_access_token
            }
            logger.info(f"[{session_id}] Fetching active job keywords from {self.active_jds_api_url} with params: {params}")
            response = requests.get(self.active_jds_api_url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success") and isinstance(data.get("keywords"), list):
                keywords = data["keywords"]
                logger.info(f"[{session_id}] Successfully fetched {len(keywords)} active job keywords: {keywords}")
                return {"keywords": keywords}
            else:
                logger.warning(f"[{session_id}] Active keywords API response 'success' is false or 'keywords' is not a list: {data}")
                return {"keywords": []}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[{session_id}] Error fetching active job keywords: {str(e)}")
            return {"keywords": []}
        except Exception as e:
            logger.error(f"[{session_id}] Unexpected error during active job keywords fetch: {str(e)}")
            return {"keywords": []}

    def process_resume_image_for_email_flow(self, image_paths: list[str], session_id: str, extracted_text: str = None, email: str = None) -> dict:
        """
        Process resume images for the email flow using a single LLM call for both parsing and matching.
        Assumes image_paths contains exactly one path to an already combined image.
        extracted_text: The text extracted from the resume (to be used by the LLM for extraction)
        email: The email address provided (optional, for context)
        """
        image_to_process_path = None
        try:
            logger.info(f"[{session_id}] Starting email resume image processing for: {image_paths}")
            if not image_paths or not isinstance(image_paths, list) or len(image_paths) != 1:
                return {
                    "status": "error",
                    "message": "Invalid image_paths provided. Expected a list with exactly one image path (combined image)."
                }

            image_to_process_path = image_paths[0]
            is_size_valid, _ = self._validate_image_size(image_to_process_path)
            if not is_size_valid:
                logger.info(f"[{session_id}] Image size exceeds threshold, will resize and compress")

            try:
                with Image.open(image_to_process_path) as img:
                    if img.format not in self.supported_formats:
                        raise ValueError(f"Unsupported image format: {img.format}. Use PNG or JPEG.")
                    img = self._resize_image(img, max_pixels=self.max_image_pixels)
                    image_bytes = self._compress_image(img, max_size_mb=self.max_image_size_mb)
                    image_format = "jpeg"
                    image_b64 = base64.b64encode(image_bytes).decode()
            except IOError as e:
                logger.error(f"[{session_id}] Failed to open image: {str(e)}")
                raise ValueError("Invalid or corrupted image file")

            # Fetch active job descriptions from the API
            jd_keywords = self._fetch_active_jd_keywords(session_id)
            if not jd_keywords:
                logger.warning(f"[{session_id}] No active job keywords fetched from API. Job matching will be impacted.")

            # Format keywords for the prompt
            keywords_list = jd_keywords.get("keywords", [])
            keywords_str = json.dumps(keywords_list, indent=2)

            # Compose prompt for LLM
            text_prompt = ""
            if extracted_text:
                text_prompt = f"\nUse the following extracted text to extract and return the email address, phone number, and parse the resume. Extract the email and phone number directly from the extracted text.\nExtracted text:\n{extracted_text}\n"
            email_context = f"\nThe provided email parameter is: {email}\n" if email else ""

            full_user_text_prompt = (
                f"Extract structured resume data from the provided image in JSON format. Include:\n"
                f"- personal_info, work_experience, education, skills, additional_info, job_matching_percentage\n"
                f"Calculate job matching based on keywords: {keywords_str}.\n"
                f"From the provided extracted text, extract and return the email address and phone number directly (do not use positions, just extract the values). Also parse the resume from the extracted text.\n"
                f"{text_prompt}"
                f"{email_context}"
                f"Return response as a JSON object with:\n"
                f"- 'parsed_resume': Structured resume data\n"
                f"- 'extracted_text': Full text extracted from the image\n"
            )

            logger.info(f"[{session_id}] Keywords being used for matching: {keywords_list}")

            messages_combined = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": full_user_text_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]

            logger.info(f"[{session_id}] Calling single LLM API for combined resume parsing and job matching.")
            combined_resp_json = self._get_llm_response(messages_combined, response_format={"type": "json_object"})

            content = combined_resp_json["choices"][0]["message"]["content"]
            llm_combined_result = json.loads(content)

            logger.info(f"--------------     >>> {llm_combined_result}")

            self._cleanup_image(image_to_process_path, session_id)
            return {
                "status": "success",
                "message": "Successfully processed resume for email flow",
                "data": {
                    "parsed_resume": llm_combined_result.get("parsed_resume", {}),
                    "extracted_text": llm_combined_result.get("extracted_text", ""),
                }
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{session_id}] HTTP error in email vision processor (single LLM call): {str(e)}")
            if image_to_process_path: self._cleanup_image(image_to_process_path, session_id)
            if e.response.status_code == 413:
                return {
                    "status": "error",
                    "message": "Image data too large for API even after resizing and compression. Try a lower resolution PDF or smaller image."
                }
            try:
                error_message = e.response.json().get("error", str(e))
            except json.JSONDecodeError:
                error_message = str(e)
            return {"status": "error", "message": f"API error in email vision processor: {error_message}"}
        except requests.exceptions.Timeout:
            logger.error(f"[{session_id}] Request timed out in email vision processor (single LLM call)")
            if image_to_process_path: self._cleanup_image(image_to_process_path, session_id)
            return {"status": "error", "message": "API request timed out. Try a smaller image or check network connection."}
        except (IOError, ValueError, requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logger.error(f"[{session_id}] Error processing resume in email vision processor (single LLM call): {str(e)}", exc_info=True)
            if image_to_process_path: self._cleanup_image(image_to_process_path, session_id)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"[{session_id}] Unexpected error in email vision processor (single LLM call): {str(e)}", exc_info=True)
            if image_to_process_path: self._cleanup_image(image_to_process_path, session_id)
            return {"status": "error", "message": "Failed to process resume image for email flow"}

email_resume_vision_processor = EmailResumeVisionProcessor()