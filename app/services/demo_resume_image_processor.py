import os
import json
import base64
import requests
import shutil
import re
from pathlib import Path
from PIL import Image
from io import BytesIO
from app.utils.logger import logger
from app.utils.prompt import DEMO_RESUME_PARSER_PROMPT

class DemoResumeImageProcessor:
    def __init__(self):
        self.api_key = os.getenv("LLM_OPEN_API_KEY_VIR")
        self.api_url = f"{os.getenv('LLM_OPEN_API_BASE_VIR')}/chat/completions"
        self.max_image_size_mb = 5
        self.max_image_pixels = 600000
        self.supported_formats = ['PNG', 'JPEG']

        if not self.api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OpenAI API key not configured")
        logger.info("ResumeImageProcessor initialized successfully")

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
            image = image.convert("L")
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

    def _extract_by_position(self, text: str, start: int, end: int) -> str:
        """Extract substring from text using start and end character positions."""
        if not text or start < 0 or end > len(text) or start > end:
            logger.warning(f"Invalid positions for extraction: start={start}, end={end}, text_length={len(text)}")
            return ""
        extracted = text[start:end].strip()
        logger.debug(f"Extracted by position ({start}, {end}): {extracted}")
        return extracted

    def _validate_email(self, email: str) -> str:
        """Validate email format using a strict regex."""
        if not email:
            return ""
        email = email.strip('.,;()[]{}<>').lower()
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email, re.IGNORECASE):
            return email
        logger.debug(f"Invalid email format: {email}")
        return ""

    def _validate_indian_phone(self, phone: str) -> str:
        """Validate if a sequence is a valid Indian phone number."""
        if not phone:
            return ""
        phone = re.sub(r'\D', '', phone)
        if len(phone) == 10 and phone[0] in '6789':
            return phone
        elif len(phone) == 12 and phone[:2] == '91' and phone[2] in '6789':
            return phone[2:]
        logger.debug(f"Invalid phone format: {phone}")
        return ""

    def _extract_email_fallback(self, text: str) -> str:
        """Extract email using regex as a fallback."""
        if not text:
            logger.warning("Empty text provided for fallback email extraction")
            return ""
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text, re.IGNORECASE)
        
        valid_emails = [self._validate_email(match) for match in matches]
        valid_emails = [email for email in valid_emails if email]
        
        if len(valid_emails) > 1:
            logger.info(f"Multiple emails found: {valid_emails}. Prioritizing based on context.")
            context_keywords = ['email', 'contact', 'personal', 'mail']
            for email in valid_emails:
                text_lower = text.lower()
                email_index = text_lower.find(email)
                if email_index != -1:
                    surrounding_text = text_lower[max(0, email_index-50):email_index+len(email)+50]
                    for keyword in context_keywords:
                        if keyword in surrounding_text.split():
                            logger.debug(f"Selected email {email} due to context: {keyword}")
                            return email
            return valid_emails[0]
        elif valid_emails:
            logger.debug(f"Email extracted by regex: {valid_emails[0]}")
            return valid_emails[0]
        
        logger.debug("No valid email found in fallback")
        return ""

    def _extract_phone_fallback(self, text: str) -> str:
        """Extract phone number using regex as a fallback."""
        if not text:
            logger.warning("Empty text provided for fallback phone extraction")
            return ""
        
        pattern = r'(?:(?:\+|0{0,2})91)?[\s\-\.\(\)\$]*?[6789][\d\s\-\.\(\)\$]{9,11}'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        valid_phones = [self._validate_indian_phone(match) for match in matches]
        valid_phones = [phone for phone in valid_phones if phone]
        
        if len(valid_phones) > 1:
            logger.info(f"Multiple phones found: {valid_phones}. Prioritizing based on context.")
            context_keywords = ['mobile', 'contact', 'phone', 'personal']
            for phone in valid_phones:
                text_lower = text.lower()
                phone_index = text_lower.find(phone)
                if phone_index != -1:
                    surrounding_text = text_lower[max(0, phone_index-50):phone_index+len(phone)+50]
                    for keyword in context_keywords:
                        if keyword in surrounding_text.split():
                            logger.debug(f"Selected phone {phone} due to context: {keyword}")
                            return phone
            return valid_phones[0]
        elif valid_phones:
            logger.debug(f"Phone extracted by regex: {valid_phones[0]}")
            return valid_phones[0]
        
        logger.debug("No valid phone found in fallback")
        return ""

    def process_resume_image(
        self, 
        image_path: str, 
        session_id: str, 
        job_title: str, 
        job_keywords: list,
        extracted_text: str = "",
        job_applicant_filled_qna: list = None,
        llm_key: str = None,
        llm_base_url: str = None,
        model: str = None
    ) -> dict:
        try:
            logger.info(f"[{session_id}] Starting resume image processing for: {image_path}")

            is_size_valid, file_size_mb = self._validate_image_size(image_path)
            if not is_size_valid:
                logger.info(f"[{session_id}] Image size exceeds threshold, will resize and compress")

            try:
                # For demo, we just validate the image exists but don't process it
                with Image.open(image_path) as img:
                    logger.info(f"[{session_id}] [DEMO] Image format: {img.format} - validation only")
                    if img.format not in self.supported_formats:
                        return {"status": "error", "message": f"Unsupported image format: {img.format}. Use PNG or JPEG."}
                    logger.info(f"[{session_id}] [DEMO] Image validated, will use text-only processing")
            except IOError as e:
                logger.error(f"[{session_id}] [DEMO] Failed to open image: {str(e)}")
                return {"status": "error", "message": "Invalid or corrupted image file"}

            if llm_key and llm_base_url and model:
                logger.info(f"[{session_id}] LLM credentials provided for resume parsing.")
                api_key = llm_key
                api_url = f"{llm_base_url}/chat/completions"
                llm_model = model
            else:
                return {"status": "error", "message": "LLM credentials not provided for resume parsing."}
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            text_prompt = ""
            if extracted_text:
                text_prompt = f"\nUse the following extracted text to extract and return the email address, phone number, and parse the resume. Extract the email and phone number directly from the extracted text.\nExtracted text:\n{extracted_text}\n"
            
            qna_prompt = ""
            if job_applicant_filled_qna:
                qna_text = "\n".join([f"Q: {qna.question}\nA: {qna.answer}" for qna in job_applicant_filled_qna])
                qna_prompt = f"\nAdditionally, consider the following job applicant Q&A responses when calculating job matching percentage:\n{qna_text}\n"

            # For demo: use normal completion API with text only, no image
            payload = {
                "model": llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": DEMO_RESUME_PARSER_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Extract structured resume data from the provided text in JSON format.
                        Calculate job matching percentage based ONLY on skills matching with required skills: {job_keywords}.
                        Applied job title: {job_title}
                        From the provided extracted text, extract and return the email address and phone number directly.
                        {text_prompt}
                        {qna_prompt}
                        Return response as a JSON object with:
                        - 'parsed_resume': Structured resume data with job_matching_percentage and interview_questions
                        - 'extracted_text': Full text extracted from the resume
                        
                        Job matching formula: (matched skills / total required skills) × 100%
                        Use format: "Skills: X% (matched: [list]) = X%. Missing skills: [list]"
                        
                        Generate 10-20 interview questions based on:
                        - Candidate's resume content and experience
                        - Applied job title: {job_title}
                        - Required skills: {job_keywords}
                        Include technical, behavioral, and situational questions relevant to the role.
                        """
                    }
                ],
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            }

            logger.info(f"[{session_id}] [DEMO] Completion API call is starting (text-only, no image): --------------->>")
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=180)
            response.raise_for_status()

            try:
                resp_json = response.json()
                content = resp_json["choices"][0]["message"]["content"]
                result = json.loads(content)
                logger.info(f"[{session_id}] [DEMO] Raw response from completion API: {result}")
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"[{session_id}] Failed to parse API response: {str(e)}")
                return {"status": "error", "message": "Invalid API response format"}

            # Remove all post-vision extraction and calculation logic (demo uses text-only processing)
            self._cleanup_image(image_path, session_id)

            # Extract all required fields from the result or set defaults
            parsed_resume = result.get("parsed_resume", {})
            extracted_text = result.get("extracted_text", "")
            job_matching_percentage = parsed_resume.get("job_matching_percentage", 0)
            interview_questions = parsed_resume.get("interview_questions", [])
            best_matched_jd_id = result.get("best_matched_jd_id", None)
            best_matched_jd_name = result.get("best_matched_jd_name", None)
            other_matching_jobs = result.get("other_matching_jobs", [])
            matching_percentage_email_flow = result.get("matching_percentage_email_flow", None)
            resume_meta_data = result.get("resume_meta_data", {})

            response = {
                "status": "success",
                "message": "Demo resume parsed successfully (text-only)",
                "data": {
                    "parsed_resume": parsed_resume,
                    "extracted_text": extracted_text,
                    "job_matching_percentage": job_matching_percentage,
                    "interview_questions": interview_questions,
                    "best_matched_jd_id": best_matched_jd_id,
                    "best_matched_jd_name": best_matched_jd_name,
                    "other_matching_jobs": other_matching_jobs,
                    "matching_percentage_email_flow": matching_percentage_email_flow,
                    "resume_meta_data": resume_meta_data
                },
                "user_id": session_id,  # Replace with actual user_id if available
                "session_id": session_id
            }
            return response

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{session_id}] [DEMO] HTTP error: {str(e)}")
            self._cleanup_image(image_path, session_id)
            try:
                error_message = e.response.json().get("error", str(e))
            except json.JSONDecodeError:
                error_message = str(e)
            return {"status": "error", "message": f"Demo API error: {error_message}"}
        except requests.exceptions.Timeout:
            logger.error(f"[{session_id}] [DEMO] Request timed out")
            self._cleanup_image(image_path, session_id)
            return {"status": "error", "message": "Demo API request timed out. Try again."}
        except (IOError, ValueError, requests.exceptions.RequestException) as e:
            logger.error(f"[{session_id}] [DEMO] Error processing resume: {str(e)}")
            self._cleanup_image(image_path, session_id)
            return {"status": "error", "message": f"Demo processing error: {str(e)}"}
        except Exception as e:
            logger.error(f"[{session_id}] [DEMO] Unexpected error: {str(e)}")
            self._cleanup_image(image_path, session_id)
            return {"status": "error", "message": "Failed to process resume in demo mode"}

demo_resume_image_processor = DemoResumeImageProcessor()
