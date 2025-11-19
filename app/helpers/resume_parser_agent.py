import json
import uuid
import os
import requests
import boto3
from openai import OpenAI
import time
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from app.utils.prompt import RESUME_PARSER_PROMPT, CONTACT_EXTRACTION_PROMPT
from app.utils.logger import logger
# from app.services.email_notifier import send_exception_email
import docx2txt
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader
import asyncio
import subprocess
from app.models.resume_parser_schema import EssentialDetails
import mammoth
from docx import Document
import zipfile
import magic

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

def clean_resume_noise(text):
    """
    Removes a wide range of OCR noise patterns from resume text, including emojis, 
    symbols, and common artifacts, while preserving valid data.
    
    Args:
        text (str): Raw OCR output from pytesseract.
    
    Returns:
        str: Cleaned text with noise patterns removed.
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid or empty text provided for noise cleaning")
        return ""
    
    # Comprehensive list of noise patterns for emojis, symbols, and OCR artifacts
    noise_patterns = [
        # Specific OCR artifacts that appear with email/contact info
        r'/envel⌢pe\s*',           # Matches "/envel⌢pe" (envelope icon artifact)
        r'♂phone\s*',              # Matches "♂phone" (phone icon artifact) 
        r'/linkedin\s*',           # Matches "/linkedin" artifacts
        r'/github\s*',             # Matches "/github" artifacts
        r'\benvel⌢pe\s*',          # Matches "envel⌢pe" variations
        r'⌢pe\s*',                # Matches "⌢pe" standalone artifacts
        
        # Generic envelope/phone icon patterns
        r'/envel[^a-zA-Z0-9@._]*',  # Matches "/envel" followed by non-alphanumeric chars (except email chars)
        r'envelope[^a-zA-Z0-9@._]*\s*', # Matches "envelope" followed by artifacts
        
        # Emojis and symbols (using Unicode ranges) - more targeted
        r'[\U0001F4E7]\s*',        # 📧 Envelope emoji
        r'[\U0001F4F1]\s*',        # 📱 Mobile phone emoji
        r'[\U0001F517]\s*',        # 🔗 Link emoji
        r'[\U0001F4DE]\s*',        # 📞 Telephone emoji
        r'[\U000026FA]\s*',        # ⛺ Tent emoji (sometimes appears as artifact)
        r'[\U00002642]\s*',        # ♂ Male sign (appears before phone)
        r'[\U000027E2]\s*',        # ⟢ Arc symbol
        
        # More specific Unicode ranges for common OCR artifacts
        r'[\U00002600-\U000026FF]\s*',  # Miscellaneous symbols
        r'[\U00002700-\U000027BF]\s*',  # Dingbats
        
        # Standalone slashes not part of URLs or valid data
        r'(?<![a-zA-Z0-9])/(?![a-zA-Z0-9])\s*',  # Standalone slashes
        
        # Bracketed artifacts
        r'\[[\w\s]+\]\s*',         # Matches bracketed artifacts like "[icon]"
        
        # Control characters and invisible characters
        r'[\x00-\x08\x0B-\x0C\x0E-\x1F]\s*',  # Control chars
        
        # Multiple whitespace normalization (keep at end)
        r'\s{2,}',                 # Replaces multiple spaces with single space
    ]
    
    logger.debug(f"Cleaning text: {repr(text[:100])}")
    
    # Apply each noise pattern to clean the text
    cleaned_text = text
    for i, pattern in enumerate(noise_patterns):
        old_text = cleaned_text
        cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
        
        # Debug logging for significant changes
        if len(old_text) - len(cleaned_text) > 5:
            logger.debug(f"Pattern {i+1} removed {len(old_text) - len(cleaned_text)} chars")
    
    # Final cleanup: normalize whitespace and strip
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    # Log the cleaning result
    if len(text) != len(cleaned_text):
        logger.info(f"Cleaned resume noise: {len(text)} -> {len(cleaned_text)} characters")
        logger.debug(f"Cleaned result: {repr(cleaned_text[:100])}")
    
    return cleaned_text

# Helper functions for cleaning and extracting contact info
# Remove unused file validation function - never called in the current flow

def extract_text_with_fallback(file_path: str, file_extension: str) -> str:
    """
    Extract text from DOC/DOCX files with multiple fallback methods.
    
    Args:
        file_path (str): Path to the document file
        file_extension (str): File extension (doc or docx)
        
    Returns:
        str: Extracted text content
    """
    text = ""
    methods_tried = []
    
    try:
        if file_extension == 'docx':
            # Method 1: Try docx2txt first (more robust with problematic files)
            try:
                text = docx2txt.process(file_path)
                methods_tried.append("docx2txt")
                if text.strip():
                    # Clean the extracted text to remove Unicode artifacts
                    cleaned_text = clean_resume_noise(text)
                    logger.info(f"Successfully extracted text using docx2txt: {len(cleaned_text)} characters")
                    return cleaned_text
            except Exception as e:
                logger.warning(f"docx2txt extraction failed: {str(e)}")
                methods_tried.append(f"docx2txt_failed: {str(e)}")
            
            # Method 2: Try mammoth as fallback
            try:
                with open(file_path, "rb") as docx_file:
                    result = mammoth.extract_raw_text(docx_file)
                    text = result.value
                    methods_tried.append("mammoth")
                    if text.strip():
                        # Clean the extracted text to remove Unicode artifacts
                        cleaned_text = clean_resume_noise(text)
                        logger.info(f"Successfully extracted text using mammoth: {len(cleaned_text)} characters")
                        return cleaned_text
            except Exception as e:
                logger.warning(f"Mammoth extraction failed: {str(e)}")
                methods_tried.append(f"mammoth_failed: {str(e)}")
            
            # Method 3: Try python-docx as last resort
            try:
                from docx import Document
                doc = Document(file_path)
                paragraphs = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        paragraphs.append(paragraph.text)
                text = '\n'.join(paragraphs)
                methods_tried.append("python_docx")
                if text.strip():
                    # Clean the extracted text to remove Unicode artifacts
                    cleaned_text = clean_resume_noise(text)
                    logger.info(f"Successfully extracted text using python-docx: {len(cleaned_text)} characters")
                    return cleaned_text
            except Exception as e:
                logger.warning(f"python-docx extraction failed: {str(e)}")
                methods_tried.append(f"python_docx_failed: {str(e)}")
        
        elif file_extension == 'doc':
            # Method 1: Try direct docx2txt on DOC file first (faster and often works)
            try:
                text = docx2txt.process(file_path)
                methods_tried.append("docx2txt_direct")
                if text.strip():
                    # Clean the extracted text to remove Unicode artifacts
                    cleaned_text = clean_resume_noise(text)
                    logger.info(f"Successfully extracted text using docx2txt directly on DOC: {len(cleaned_text)} characters")
                    return cleaned_text
            except Exception as e:
                logger.warning(f"Direct docx2txt on DOC failed: {str(e)}")
                methods_tried.append(f"docx2txt_direct_failed: {str(e)}")
            
            # Method 2: Try converting to docx (requires LibreOffice)
            try:
                output_dir = Path(file_path).parent
                converted_docx_path = convert_doc_to_docx(file_path, output_dir)
                
                # Try to extract from converted docx
                if os.path.exists(converted_docx_path):
                    # Try multiple extraction methods on the converted file
                    text = ""
                    
                    # Try mammoth first
                    try:
                        with open(converted_docx_path, "rb") as docx_file:
                            result = mammoth.extract_raw_text(docx_file)
                            text = result.value
                            methods_tried.append("doc_to_docx_mammoth")
                    except Exception as mammoth_err:
                        logger.warning(f"Mammoth failed on converted DOCX: {str(mammoth_err)}")
                        
                        # Try docx2txt as fallback
                        try:
                            text = docx2txt.process(converted_docx_path)
                            methods_tried.append("doc_to_docx_docx2txt")
                        except Exception as docx2txt_err:
                            logger.warning(f"docx2txt failed on converted DOCX: {str(docx2txt_err)}")
                    
                    # Clean up converted file
                    if os.path.exists(converted_docx_path):
                        os.remove(converted_docx_path)
                    
                    if text and text.strip():
                        # Clean the extracted text to remove Unicode artifacts
                        cleaned_text = clean_resume_noise(text)
                        logger.info(f"Successfully extracted text via DOC->DOCX conversion: {len(cleaned_text)} characters")
                        return cleaned_text
            except Exception as e:
                logger.warning(f"DOC to DOCX conversion failed (LibreOffice may not be available): {str(e)}")
                methods_tried.append(f"doc_conversion_failed: {str(e)}")
            
            # Method 3: Try python-docx direct reading (may work for some DOC files)
            try:
                from docx import Document
                doc = Document(file_path)
                paragraphs = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        paragraphs.append(paragraph.text)
                text = '\n'.join(paragraphs)
                methods_tried.append("python_docx_direct")
                if text.strip():
                    # Clean the extracted text to remove Unicode artifacts
                    cleaned_text = clean_resume_noise(text)
                    logger.info(f"Successfully extracted text using python-docx directly: {len(cleaned_text)} characters")
                    return cleaned_text
            except Exception as e:
                logger.warning(f"python-docx direct reading failed: {str(e)}")
                methods_tried.append(f"python_docx_failed: {str(e)}")
            
            # Method 4: Try textract if available (for legacy DOC files)
            try:
                import textract
                text = textract.process(file_path).decode('utf-8')
                methods_tried.append("textract")
                if text.strip():
                    # Clean the extracted text to remove Unicode artifacts
                    cleaned_text = clean_resume_noise(text)
                    logger.info(f"Successfully extracted text using textract: {len(cleaned_text)} characters")
                    return cleaned_text
            except ImportError:
                logger.debug("textract not available, skipping")
                methods_tried.append("textract_not_available")
            except Exception as e:
                logger.warning(f"textract extraction failed: {str(e)}")
                methods_tried.append(f"textract_failed: {str(e)}")
        
        logger.warning(f"All text extraction methods failed for {file_extension} file. Methods tried: {methods_tried}")
        return ""
        
    except Exception as e:
        logger.error(f"Error in fallback text extraction: {str(e)}")
        return ""

def clean_text(text: str) -> str:
    """Clean text by normalizing spaces, handling OCR errors, removing Unicode noise, and separating concatenated strings."""
    if not text or not isinstance(text, str):
        logger.warning("Invalid or empty text provided for cleaning")
        return ""
    
    # First, remove Unicode noise and OCR artifacts
    text = clean_resume_noise(text)
    
    # Replace tabs, newlines, and multiple spaces with a single space
    text = re.sub(r'[\n\r\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text.strip())
    # Insert space between digits and letters to handle concatenation (e.g., "8808712755shashank")
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    return text


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using PyPDF2 with Unicode noise cleaning.
    
    Args:
        pdf_path (str): Path to PDF file
        
    Returns:
        str: Extracted and cleaned text from PDF
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page_number, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # Clean the extracted text immediately to remove Unicode artifacts
                cleaned_page_text = clean_resume_noise(page_text)
                text += cleaned_page_text + "\n"
                logger.debug(f"Page {page_number+1} - Raw: {repr(page_text[:100])}")
                logger.debug(f"Page {page_number+1} - Cleaned: {repr(cleaned_page_text[:100])}")
            else:
                # Convert page to image and use OCR
                images = convert_from_path(pdf_path, first_page=page_number+1, last_page=page_number+1)
                for image in images:
                    ocr_text = pytesseract.image_to_string(image)
                    # Clean OCR text as well
                    cleaned_ocr_text = clean_resume_noise(ocr_text)
                    text += cleaned_ocr_text + "\n"
                    logger.debug(f"Page {page_number+1} OCR - Raw: {repr(ocr_text[:100])}")
                    logger.debug(f"Page {page_number+1} OCR - Cleaned: {repr(cleaned_ocr_text[:100])}")
        
        # Final cleaning pass to ensure consistency
        final_cleaned_text = clean_resume_noise(text)
        logger.info(f"PDF text extraction completed - Final length: {len(final_cleaned_text)} characters")
        return final_cleaned_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def get_file_extension_from_url(url: str) -> str:
    """
    Extract file extension from URL, handling pre-signed URLs.
    
    Args:
        url (str): URL of the file
        
    Returns:
        str: File extension in lowercase
    """
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        if 'response-content-disposition' in query_params:
            disposition = query_params['response-content-disposition'][0]
            if 'filename=' in disposition:
                filename = disposition.split('filename=')[1].strip('"')
                if '.' in filename:
                    return filename.split('.')[-1].lower()
        
        if '.' in path:
            return path.split('.')[-1].lower()
            
        if 'response-content-type' in query_params:
            content_type = query_params['response-content-type'][0]
            if 'pdf' in content_type:
                return 'pdf'
            elif 'docx' in content_type:
                return 'docx'
            elif 'doc' in content_type:
                return 'doc'
        
        return ''
    except Exception as e:
        logger.error(f"Error extracting file extension: {str(e)}")
        return ''

def download_from_s3(s3_url: str) -> tuple[bytes, str]:
    """
    Download file from S3 URL.
    
    Args:
        s3_url (str): S3 URL of the file
        
    Returns:
        tuple[bytes, str]: File content and file extension
    """
    try:
        parsed_url = urlparse(s3_url)
        bucket_name = parsed_url.netloc
        object_key = parsed_url.path.lstrip('/')
        
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()
        
        file_extension = get_file_extension_from_url(s3_url)
        
        return file_content, file_extension
    except Exception as e:
        logger.error(f"Error downloading from S3: {str(e)}")
        raise

def download_from_url(url: str) -> tuple[bytes, str]:
    """
    Download file from regular URL with enhanced validation.
    
    Args:
        url (str): URL of the file
        
    Returns:
        tuple[bytes, str]: File content and file extension
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Check response size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) < 500:
            logger.warning(f"Response content-length is very small: {content_length} bytes")
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' in content_type:
            logger.error(f"Server returned HTML content instead of file. Content-Type: {content_type}")
            raise Exception(f"Server returned HTML content (Content-Type: {content_type}) instead of the requested file")
        
        # Check if response content looks like an error page
        content_preview = response.content[:500].lower()
        if b'<html' in content_preview or b'error' in content_preview or b'not found' in content_preview:
            logger.error(f"Response appears to be an error page: {response.content[:200]}")
            raise Exception("Server returned an error page instead of the requested file")
        
        file_extension = get_file_extension_from_url(url)
        
        logger.info(f"Successfully downloaded {len(response.content)} bytes, Content-Type: {content_type}")
        return response.content, file_extension
    except Exception as e:
        logger.error(f"Error downloading from URL: {str(e)}")
        raise


def convert_doc_to_docx(doc_path: str, output_dir: Path) -> str:
    """
    Convert a .doc file to .docx using LibreOffice CLI.
    Args:
        doc_path (str): Path to the .doc file
        output_dir (Path): Directory to save the .docx file
    Returns:
        str: Path to the converted .docx file
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "soffice", "--headless", "--convert-to", "docx", "--outdir", str(output_dir), str(doc_path)
        ], check=True)
        docx_path = output_dir / (Path(doc_path).stem + ".docx")
        if not docx_path.exists():
            raise Exception("DOCX file not created")
        return str(docx_path)
    except Exception as e:
        logger.error(f"Error converting .doc to .docx: {str(e)}")
        raise

def process_resume_file(resume_url: str, session_id: str = None) -> dict:
    """
    Extract text from resume URL (PDF/DOCX/DOC or S3).
    Args:
        resume_url (str): URL of the resume (PDF/DOCX/DOC or S3)
    Returns:
        dict: A dictionary containing the extracted text and status
    """
    try:
        # Validate URL
        if not resume_url or not isinstance(resume_url, str):
            logger.error("Invalid resume URL provided")
            return {
                "status": "error",
                "message": "Invalid resume URL provided"
            }
        
        # Download file based on URL type
        if resume_url.startswith('s3://'):
            file_content, file_extension = download_from_s3(resume_url)
        else:
            if not resume_url.startswith(('http://', 'https://')):
                logger.error(f"Invalid URL format: {resume_url}")
                return {
                    "status": "error",
                    "message": "Invalid URL format. URL must start with http://, https://, or s3://"
                }
            file_content, file_extension = download_from_url(resume_url)
        
        # Validate file extension
        if not file_extension or file_extension not in ['pdf', 'docx', 'doc']:
            logger.error(f"Unsupported file extension: {file_extension}")
            return {
                "status": "error",
                "message": f"Unsupported file extension: {file_extension}. Supported formats: PDF, DOCX, DOC"
            }
            
        # Save the file temporarily for text extraction
        import time
        import tempfile
        timestamp = int(time.time() * 1000)  # millisecond timestamp for uniqueness
        session_prefix = session_id or f"nosession_{uuid.uuid4().hex[:8]}"
        
        # Create a temp directory for this session
        temp_dir = Path(tempfile.gettempdir()) / f"resume_parser_{session_prefix}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file = temp_dir / f"resume_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        with open(temp_file, 'wb') as f:
            f.write(file_content)

        # Basic file validation - only check for obvious issues
        try:
            file_size = os.path.getsize(temp_file)
            
            # Enhanced size check based on file type
            min_size_by_type = {
                'pdf': 1000,  # PDFs are typically at least 1KB
                'docx': 2000,  # DOCX files are ZIP archives, typically at least 2KB  
                'doc': 2000   # DOC files have header structure, typically at least 2KB
            }
            
            min_expected_size = min_size_by_type.get(file_extension, 100)
            
            if file_size < min_expected_size:
                logger.warning(f"File is very small ({file_size} bytes) for a {file_extension} file. Expected at least {min_expected_size} bytes.")
                
                # For very small files, this is almost certainly not a valid document
                if file_size < 500:  # Too small for any real document
                    # Try to read the content to see what we actually got
                    try:
                        with open(temp_file, 'rb') as f:
                            content_sample = f.read()
                        
                        # Try to decode and see if it's error text
                        try:
                            text_content = content_sample.decode('utf-8', errors='ignore')
                            logger.error(f"File content appears to be: {text_content[:200]}")
                        except:
                            logger.error(f"File contains binary data: {content_sample[:50]}")
                    except Exception as e:
                        logger.error(f"Could not read file content: {str(e)}")
                    
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return {
                        "status": "error", 
                        "message": f"Downloaded file is too small ({file_size} bytes) to be a valid {file_extension.upper()} document. The server may have returned an error response instead of the actual file."
                    }
            
            # Check if it's HTML (common when servers return error pages)
            with open(temp_file, 'rb') as f:
                first_bytes = f.read(min(1024, file_size)).lower()
                if b'<html' in first_bytes or b'<!doctype html' in first_bytes:
                    logger.error(f"File appears to be HTML content, not a document")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return {
                        "status": "error",
                        "message": "Downloaded file appears to be HTML content (likely an error page), not a document"
                    }
                
                # Check for other common error indicators
                if file_size < 500 and any(error_text in first_bytes for error_text in [
                    b'error', b'not found', b'access denied', b'forbidden', b'unauthorized'
                ]):
                    logger.error(f"File appears to contain error text: {first_bytes[:200]}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return {
                        "status": "error",
                        "message": f"Downloaded file appears to contain error content. File size: {file_size} bytes"
                    }
            
            logger.info(f"Basic file validation passed. File size: {file_size} bytes, extension: {file_extension}")
            
        except Exception as e:
            logger.warning(f"Basic file validation failed: {str(e)}. Attempting to process anyway...")

        # Extract text based on file type
        extracted_text = ""
        
        # Handle DOCX or DOC files
        if file_extension in ['docx', 'doc']:
            try:
                # Use the robust text extraction with fallback methods
                extracted_text = extract_text_with_fallback(str(temp_file), file_extension)
                
                if not extracted_text or not extracted_text.strip():
                    logger.warning(f"Standard text extraction failed for {file_extension} file. Attempting raw byte extraction...")
                    
                    # Last resort: Try to extract readable text from raw bytes
                    if file_extension == 'doc':
                        try:
                            with open(temp_file, 'rb') as f:
                                raw_content = f.read()
                            
                            # Attempt to decode as various encodings
                            for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                                try:
                                    decoded_text = raw_content.decode(encoding, errors='ignore')
                                    # Filter out non-printable characters but keep spaces and newlines
                                    readable_text = ''.join(c for c in decoded_text if c.isprintable() or c in '\n\r\t ')
                                    if len(readable_text.strip()) > 10:  # Found some readable content
                                        extracted_text = readable_text
                                        logger.info(f"Extracted text from raw bytes using {encoding} encoding: {len(extracted_text)} characters")
                                        break
                                except UnicodeDecodeError:
                                    continue
                        except Exception as raw_e:
                            logger.warning(f"Raw byte extraction failed: {str(raw_e)}")
                    
                    if not extracted_text or not extracted_text.strip():
                        logger.error(f"All extraction methods failed for {file_extension} file")
                        os.remove(temp_file)
                        return {
                            "status": "error",
                            "message": f"No text could be extracted from {file_extension} file. File appears to be corrupted, password-protected, or extremely small."
                        }
                
                # Clean up the temporary file
                os.remove(temp_file)
                
                return {
                    "status": "success",
                    "message": "Successfully extracted text from DOC/DOCX",
                    "data": {
                        "extracted_text": extracted_text
                    }
                }
            except Exception as e:
                logger.error(f"Error processing DOCX/DOC file: {str(e)}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return {
                    "status": "error",
                    "message": f"Error processing DOCX/DOC file: {str(e)}"
                }
        
        # Handle PDF files
        elif file_extension == 'pdf':
            try:
                # Extract text from PDF
                extracted_text = extract_text_from_pdf(str(temp_file))
                
                logger.info(f"Text extraction done! Extracted {len(extracted_text)} characters")
                
                # Clean up the temporary PDF file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                return {
                    "status": "success",
                    "message": "Successfully extracted text from PDF",
                    "data": {
                        "extracted_text": extracted_text
                    }
                }
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {str(e)}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return {
                    "status": "error",
                    "message": f"Error extracting text from PDF: {str(e)}"
                }
        else:
            # This case should not be reached with current logic
            logger.error(f"Unexpected file extension after processing: {file_extension}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return {
                "status": "error",
                "message": f"Unexpected file extension: {file_extension}"
            }
    except Exception as e:
        logger.error(f"Error extracting text from resume: {str(e)}")
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
        return {
            "status": "error",
            "message": str(e)
        }


async def extract_essential_details_from_text(
    extracted_text: str,
    llm_key: str = None,
    llm_base_url: str = None,
    model: str = None,
    session_id: str = None
) -> dict:
    """
    Quick extraction of only essential contact details (first_name, last_name, email, mobile_number)
    using already extracted text and LLM API call.
    
    Args:
        extracted_text (str): Already extracted text from resume
        llm_key (str): LLM API key
        llm_base_url (str): LLM base URL
        model (str): LLM model name
        session_id (str): Session ID for logging
        
    Returns:
        dict: Contains status and essential details
    """
    if not session_id:
        session_id = f"essential_{uuid.uuid4().hex[:8]}"
        
    try:
        logger.info(f"Quick extraction of essential details from extracted text")
        
        if not extracted_text.strip():
            return {
                "status": "error",
                "message": "No text provided for essential details extraction"
            }

        # Use LLM to extract essential details
        if not all([llm_key, llm_base_url, model]):
            return {
                "status": "error",
                "message": "LLM credentials not provided"
            }
        
        # Use OpenAI client with structured parsing
        try:
            client = OpenAI(
                api_key=llm_key,
                base_url=llm_base_url
            )
            logger.info("openai client initialized")
            completion = client.responses.parse(
                model=model,
                input=[
                    {
                        "role": "system", 
                        "content": CONTACT_EXTRACTION_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"Extract essential details from this resume text:\n\n{extracted_text}"
                    }
                ],
                text_format=EssentialDetails,
            )
            
            
            essential_details = completion.output_parsed
            logger.info(f"LLM extracted data: {essential_details.model_dump()}")
        except Exception as api_error:
            logger.error(f"OpenAI API error: {str(api_error)}")
            raise api_error
        
        logger.info(f"Essential details extracted successfully")
        return {
            "status": "success",
            "data": essential_details.model_dump(),
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error in quick essential extraction: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }


def _is_valid_param(value) -> bool:
    """Check if a parameter has a valid value (not None, not empty string)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def normalize_job_matching_percentage(percentage: any) -> int:
    """
    Normalize job matching percentage to ensure it's always a valid integer between 0-100.
    
    Args:
        percentage: The percentage value (can be float, int, string, or None)
        
    Returns:
        int: Valid percentage between 0-100 (inclusive), defaults to 0 if None/invalid
    """
    if percentage is None:
        return 0
    
    try:
        # Convert to float first
        if isinstance(percentage, str):
            percentage = percentage.strip()
            if not percentage:  # Empty string
                return 0
            percentage = float(percentage)
        
        percentage = float(percentage)
        
        # Round to nearest integer
        percentage = round(percentage)
        
        # Ensure it's between 0-100
        if percentage < 0:
            return 0
        elif percentage > 100:
            return 100
        else:
            return percentage
            
    except (ValueError, TypeError):
        # If conversion fails, return 0 as fallback
        return 0


def normalize_evaluation_level(level: any) -> str:
    """
    Normalize evaluation criteria level to ensure it's always a valid level (L0-L4).
    Handles None, empty strings, "null", "NULL", or any invalid values.
    
    Args:
        level: The level value (can be string, None, or any other type)
        
    Returns:
        str: Valid level (L0, L1, L2, L3, or L4), defaults to "L0" if None/invalid
    """
    # Handle None, empty, or invalid values
    if level is None:
        return "L0"
    
    # Convert to string and normalize
    try:
        level_str = str(level).strip().upper()
        
        # Handle empty string
        if not level_str:
            return "L0"
        
        # Handle "null" or "NULL" strings
        if level_str in ["NULL", "NONE"]:
            return "L0"
        
        # Validate if it's a proper level format (L0-L4)
        valid_levels = ["L0", "L1", "L2", "L3", "L4"]
        if level_str in valid_levels:
            return level_str
        
        # If not a valid level, default to L0
        logger.warning(f"Invalid evaluation level '{level}' provided, defaulting to L0")
        return "L0"
        
    except Exception as e:
        logger.warning(f"Error normalizing evaluation level '{level}': {str(e)}, defaulting to L0")
        return "L0"




def transform_parsed_data_to_api_payload(parsed_resume_data: dict, extracted_text: str) -> dict:
    """
    Transform parsed resume data to the format expected by the update job applicant API.
    Only includes fields with actual values to avoid overwriting existing data.
    EXCLUDES first_name, last_name, email, mobile_no as they're already sent in first response.
    
    Args:
        parsed_resume_data: Full parsed data from vision processing
        extracted_text: Text extracted from resume
        
    Returns:
        dict: Transformed data in API payload format with only non-empty values
    """
    if not parsed_resume_data:
        return {}
    
    personal_info = parsed_resume_data.get("personal_info", {})
    skills = parsed_resume_data.get("skills", {})
    resume_meta_data = parsed_resume_data.get("resume_meta_data", {})
    
    # Helper function to only add non-empty values
    def add_if_not_empty(target_dict: dict, key: str, value) -> None:
        if value and value != "" and value != [] and value != {} and value is not False:
            target_dict[key] = value
    
    # Transform to API payload format with only non-empty values
    api_payload = {}
    
    # SKIP: first_name, last_name, email, mobile_no (already sent in first response)
    
    # Basic personal information
    add_if_not_empty(api_payload, "gender", personal_info.get("gender"))
    add_if_not_empty(api_payload, "dob", personal_info.get("dob"))
    add_if_not_empty(api_payload, "doj", personal_info.get("doj"))
    add_if_not_empty(api_payload, "father_name", personal_info.get("father_name"))
    add_if_not_empty(api_payload, "marital_status", personal_info.get("marital_status"))
    add_if_not_empty(api_payload, "nationality", personal_info.get("nationality"))
    
    # Professional information
    add_if_not_empty(api_payload, "current_designation", personal_info.get("current_designation"))
    add_if_not_empty(api_payload, "current_organization", personal_info.get("current_organization"))
    add_if_not_empty(api_payload, "designation", personal_info.get("designation"))
    add_if_not_empty(api_payload, "post", personal_info.get("post"))
    
    # Address and location information
    add_if_not_empty(api_payload, "corresponding_address", personal_info.get("corresponding_address"))
    add_if_not_empty(api_payload, "permanent_address", personal_info.get("permanent_address"))
    add_if_not_empty(api_payload, "job_location", personal_info.get("job_location"))
    add_if_not_empty(api_payload, "posting_location", personal_info.get("posting_location"))
    add_if_not_empty(api_payload, "job_city", personal_info.get("job_city"))
    add_if_not_empty(api_payload, "job_state", personal_info.get("job_state"))
    add_if_not_empty(api_payload, "job_state_code", personal_info.get("job_state_code"))
    
    # Social profiles
    add_if_not_empty(api_payload, "linkedin_url", personal_info.get("linkedin_url"))
    add_if_not_empty(api_payload, "github_url", personal_info.get("github_url"))
    add_if_not_empty(api_payload, "portfolio_url", personal_info.get("portfolio_url"))
    add_if_not_empty(api_payload, "personal_website", personal_info.get("personal_website"))
    
    # Experience information
    add_if_not_empty(api_payload, "year", personal_info.get("total_working_experience_in_year"))
    add_if_not_empty(api_payload, "month", personal_info.get("total_working_experience_in_month"))
    add_if_not_empty(api_payload, "total_working_experience_text", personal_info.get("total_working_experience_text"))
    add_if_not_empty(api_payload, "notice_period", personal_info.get("notice_period"))
    add_if_not_empty(api_payload, "last_working_day", personal_info.get("last_working_day"))
    
    # Handle serving_notice separately as it can be boolean False
    if personal_info.get("serving_notice") is not None:
        api_payload["serving_notice"] = personal_info["serving_notice"]
    
    # Financial information
    add_if_not_empty(api_payload, "current_ctc", personal_info.get("current_ctc"))
    add_if_not_empty(api_payload, "expected_ctc", personal_info.get("expected_ctc"))
    add_if_not_empty(api_payload, "offer_ctc", personal_info.get("offer_ctc"))
    
    # Status information
    add_if_not_empty(api_payload, "status", personal_info.get("status"))
    add_if_not_empty(api_payload, "current_status", personal_info.get("current_status"))
    add_if_not_empty(api_payload, "state", personal_info.get("state"))
    add_if_not_empty(api_payload, "reason", personal_info.get("reason"))
    add_if_not_empty(api_payload, "applied_on", personal_info.get("applied_on"))
    
    # Skills - combine all skills into a single string (only if skills object has content)
    all_skills = []
    if skills and skills != {}:
        if skills.get("technical_skills") and isinstance(skills["technical_skills"], list):
            all_skills.extend(skills["technical_skills"])
        if skills.get("soft_skills") and isinstance(skills["soft_skills"], list):
            all_skills.extend(skills["soft_skills"])
        if skills.get("certifications") and isinstance(skills["certifications"], list):
            all_skills.extend(skills["certifications"])
    
    if all_skills:
        api_payload["skills"] = ", ".join(all_skills)
    
    # About applicant and notes
    add_if_not_empty(api_payload, "about_applicant", personal_info.get("about_applicant"))
    add_if_not_empty(api_payload, "note", personal_info.get("note"))
    
    # Job matching percentage (always include, normalize to 0 if invalid)
    job_percentage = normalize_job_matching_percentage(personal_info.get("job_matching_percentage"))
    api_payload["ai_predicted_job_match_percentage"] = job_percentage
    
    # Additional information
    add_if_not_empty(api_payload, "pan_number", personal_info.get("pan_number"))
    add_if_not_empty(api_payload, "aadhar_number", personal_info.get("aadhar_number"))
    
    # Handle passport_available separately as it can be boolean False
    if personal_info.get("passport_available") is not None:
        api_payload["passport_available"] = personal_info["passport_available"]
    
    # Tag IDs
    add_if_not_empty(api_payload, "tag_ids", personal_info.get("tag_ids"))
    
    # Resume text content - only add if there's actual content
    if parsed_resume_data:
        api_payload["parsed_resume"] = json.dumps(parsed_resume_data)
    add_if_not_empty(api_payload, "resume_extracted_text", extracted_text)
    
    return api_payload


def create_standard_response_format(
    essential_details: dict = None,
    extracted_text: str = "",
    parsed_resume_data: dict = None,
    session_id: str = "",
    user_id: str = "",
    job_matching_percentage: float = None,
    best_matched_jd_id: str = None,
    best_matched_jd_name: str = None,
    other_matching_jobs: list = None,
    matching_percentage_email_flow: float = None,
    is_initial_response: bool = True
) -> dict:
    """
    Create standardized response format for both immediate and background responses.
    Maintains consistent structure while only including fields with actual values.
    
    Args:
        essential_details: Basic contact info from quick extraction
        extracted_text: Text extracted from resume
        parsed_resume_data: Full parsed data from vision processing
        session_id: Session identifier
        user_id: User identifier  
        job_matching_percentage: Job matching score
        best_matched_jd_id: Best matched job description ID
        best_matched_jd_name: Best matched job description name
        other_matching_jobs: List of other matching jobs
        matching_percentage_email_flow: Email flow matching percentage
        is_initial_response: Whether this is the initial quick response
        
    Returns:
        dict: Standardized response format with consistent structure
    """
    
    # Helper function to only add non-empty values
    def add_if_not_empty(target_dict: dict, key: str, value) -> None:
        if value and value != "" and value != [] and value != {}:
            target_dict[key] = value
    
    # Initialize essential details safely
    if essential_details is None:
        essential_details = {}
    
    if other_matching_jobs is None:
        other_matching_jobs = []
    
    # Create personal_info structure with only non-empty values
    personal_info = {}
    
    # Add essential details if they exist
    add_if_not_empty(personal_info, "first_name", essential_details.get("first_name"))
    add_if_not_empty(personal_info, "last_name", essential_details.get("last_name"))
    add_if_not_empty(personal_info, "email", essential_details.get("email"))
    add_if_not_empty(personal_info, "mobile_no", essential_details.get("mobile_number"))
    
    # Add job matching percentage (normalize to ensure it's always a valid value)
    normalized_job_percentage = normalize_job_matching_percentage(job_matching_percentage)
    personal_info["job_matching_percentage"] = normalized_job_percentage
    
    # If we have full parsed data from vision processing, merge it
    if parsed_resume_data and not is_initial_response:
        vision_personal_info = parsed_resume_data.get("personal_info", {})
        for key, value in vision_personal_info.items():
            add_if_not_empty(personal_info, key, value)
    
    # Create skills structure - only include if there are actual skills
    skills = {}
    has_skills = False
    
    if parsed_resume_data and not is_initial_response:
        vision_skills = parsed_resume_data.get("skills", {})
        if vision_skills.get("technical_skills"):
            skills["technical_skills"] = vision_skills["technical_skills"]
            has_skills = True
        if vision_skills.get("soft_skills"):
            skills["soft_skills"] = vision_skills["soft_skills"]
            has_skills = True
        if vision_skills.get("certifications"):
            skills["certifications"] = vision_skills["certifications"]
            has_skills = True
    
    # If no skills found, keep as empty object
    if not has_skills:
        skills = {}
    
    # Create resume_meta_data structure - only include if there's actual data
    resume_meta_data = {}
    has_meta_data = False
    
    if parsed_resume_data and not is_initial_response:
        vision_meta_data = parsed_resume_data.get("resume_meta_data", {})
        if vision_meta_data.get("experience"):
            resume_meta_data["experience"] = vision_meta_data["experience"]
            has_meta_data = True
        if vision_meta_data.get("education"):
            resume_meta_data["education"] = vision_meta_data["education"]
            has_meta_data = True
        if vision_meta_data.get("skills"):
            resume_meta_data["skills"] = vision_meta_data["skills"]
            has_meta_data = True
        if vision_meta_data.get("projects"):
            resume_meta_data["projects"] = vision_meta_data["projects"]
            has_meta_data = True
        
        # Add other fields if they exist
        for key, value in vision_meta_data.items():
            if key not in ["experience", "education", "skills", "projects"]:
                if value and value != "" and value != [] and value != {}:
                    resume_meta_data[key] = value
                    has_meta_data = True
    
    # If no meta data found, keep as empty object
    if not has_meta_data:
        resume_meta_data = {}
    
    # Create parsed_resume structure based on response type
    if is_initial_response:
        # For initial response, only include personal_info
        parsed_resume = {
            "personal_info": personal_info
        }
    else:
        # For final response, include all sections (even if empty for consistency)
        parsed_resume = {
            "personal_info": personal_info,
            "skills": skills,
            "resume_meta_data": resume_meta_data
        }
        
        # Add interview questions if available
        if parsed_resume_data:
            interview_questions = parsed_resume_data.get("interview_questions", [])
            if interview_questions:
                parsed_resume["interview_questions"] = interview_questions
    
    # Determine message based on response type
    if is_initial_response:
        message = "Essential details extracted, full parsing in progress"
    else:
        message = "Resume parsed successfully"
    
    # Build response data - only include fields with actual values
    response_data = {
        "parsed_resume": parsed_resume,
        "extracted_text": extracted_text
    }
    
    # Add job matching percentage (always include with normalization to 0 if None)
    normalized_job_percentage = normalize_job_matching_percentage(job_matching_percentage)
    response_data["job_matching_percentage"] = normalized_job_percentage
    
    # Add email flow matching percentage (always include with normalization to 0 if None)
    normalized_email_flow_percentage = normalize_job_matching_percentage(matching_percentage_email_flow)
    response_data["matching_percentage_email_flow"] = normalized_email_flow_percentage
    
    # Only add other fields if they have actual values
    if best_matched_jd_id:
        response_data["best_matched_jd_id"] = best_matched_jd_id
    if best_matched_jd_name:
        response_data["best_matched_jd_name"] = best_matched_jd_name
    if other_matching_jobs:
        response_data["other_matching_jobs"] = other_matching_jobs
    
    return {
        "status": "success",
        "message": message,
        "data": response_data,
        "user_id": user_id,
        "session_id": session_id
    }


async def call_update_job_applicant_api(
    company_id: str,
    job_applicant_id: str,
    parsed_resume_data: dict,
    extracted_text: str,
    resume_parser_access_token: str,
    origin: str = None,
    session_id: str = None,
    is_evaluation_report: bool = False,
    job_matching_percentage: float = None,
    matching_percentage_email_flow: float = None
) -> bool:
    """
    Call the API to update job applicant with parsed resume data.
    
    Args:
        company_id: Company identifier
        job_applicant_id: Job applicant identifier
        parsed_resume_data: Parsed resume data from vision processing
        extracted_text: Extracted text from resume
        resume_parser_access_token: Token for API authentication
        origin: Origin domain
        session_id: Session ID for logging
        is_evaluation_report: If True, wraps payload in evaluation_report format
        job_matching_percentage: Job matching percentage (for evaluation reports)
        matching_percentage_email_flow: Email flow matching percentage (for evaluation reports)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if is_evaluation_report:
            # For evaluation reports, use the nested evaluation_report structure
            normalized_job_percentage = normalize_job_matching_percentage(job_matching_percentage)
            normalized_email_flow = normalize_job_matching_percentage(matching_percentage_email_flow)
            
            api_payload = {
                "evaluation_report": {
                    "parsed_resume": parsed_resume_data,
                    "job_matching_percentage": normalized_job_percentage,
                    "matching_percentage_email_flow": normalized_email_flow
                }
            }
            logger.info(f"Using evaluation_report format for API update")
            logger.info(f"Evaluation report - Job matching: {normalized_job_percentage}%, Email flow: {normalized_email_flow}%")
        else:
            # For regular parsing (no evaluation), use the flattened format
            api_payload = transform_parsed_data_to_api_payload(parsed_resume_data, extracted_text)
            logger.info(f"Using standard flattened format for API update (no evaluation)")
        
        if not api_payload:
            logger.warning(f"No data to update for job applicant {job_applicant_id}")
            return False
        
        # Construct API URL
        api_url = f"{origin}api/v1/company/{company_id}/update_job_applicant/{job_applicant_id}"
        logger.info(f"API URL: {api_url}")
        logger.info(f"Token: {resume_parser_access_token}")

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "resume-parser-access-token": resume_parser_access_token
        }
        
        # Add origin header if provided
        if origin:
            headers["Origin"] = origin
        
        logger.info(f"Making API call to update job applicant: {api_url}")
        response = requests.put(
            api_url,
            headers=headers,
            data=json.dumps(api_payload),
            timeout=180
        )
        

        if response.status_code == 200:
            logger.info(f"Successfully updated job applicant {job_applicant_id}")
            return True
        else:
            logger.error(f"Failed to update job applicant. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"API call timed out for job applicant {job_applicant_id}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed for job applicant {job_applicant_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in API call for job applicant {job_applicant_id}: {str(e)}")
        return False


def _analyze_resume_with_text_completion(
    extracted_text: str,
    job_applicant_id: str,
    session_id: str,
    job_title: str = None,
    job_keywords: list = None,
    job_applicant_filled_qna: list = None,
    evaluation_criteria: list = None,
    job_profile_details: dict = None,
    min_experience: int = None,
    max_experience: int = None,
    llm_key: str = None,
    llm_base_url: str = None,
    model: str = None
) -> dict:
    """
    Analyze resume text using completion API (non-vision).
    
    Args:
        extracted_text: Text extracted from resume
        job_applicant_id: Job applicant identifier
        session_id: Session identifier
        job_title: Job title for matching
        job_keywords: Keywords for job matching
        job_applicant_filled_qna: Pre-filled QNA data
        evaluation_criteria: Evaluation criteria for scoring
        job_profile_details: Detailed job profile information
        llm_key: LLM API key
        llm_base_url: LLM base URL
        model: LLM model name
        
    Returns:
        dict: Parsed resume data with status
    """
    try:
        logger.info(f"Starting text-based resume analysis for: {job_applicant_id}")
        logger.info(f"Evaluation criteria: {evaluation_criteria}")
        logger.info(f"Job profile details: {job_profile_details}")
        logger.info(f"Model: {model}")

        if not llm_key or not llm_base_url or not model:
            return {"status": "error", "message": "LLM credentials not provided for resume parsing."}

        # Build context data for resume parsing
        context_parts = []
        
        # Add extracted text (sanitize to prevent JSON issues)
        if extracted_text:
            # Clean the text to prevent JSON parsing issues
            sanitized_text = extracted_text.replace('\r\n', '\n').replace('\r', '\n')
            # Limit text length to prevent token overflow (keep reasonable limit)
            max_text_length = 15000  # Approximately 4000 tokens worth of text
            if len(sanitized_text) > max_text_length:
                logger.warning(f"Extracted text is very long ({len(sanitized_text)} chars), truncating to {max_text_length} chars")
                sanitized_text = sanitized_text[:max_text_length] + "\n... (text truncated due to length)"
            context_parts.append(f"Extracted Text:\n{sanitized_text}")
        
        # Add evaluation criteria if provided
        if evaluation_criteria:
            logger.info(f"Using {len(evaluation_criteria)} evaluation criteria (Level-Based L0-L4)")
            criteria_list = []
            
            for c in evaluation_criteria:
                # Normalize level to handle None, empty strings, "null", etc. - defaults to L0
                raw_level = c.level if hasattr(c, 'level') else None
                normalized_level = normalize_evaluation_level(raw_level)
                criteria_list.append(f"- {c.parameter_name} [Level: {normalized_level}]: {c.description}")
            
            context_parts.append(f"Evaluation Criteria (Level-Based - Score each 0-100%, calculate average):\n" + "\n".join(criteria_list))
        
        # Add job profile details if provided
        if job_profile_details:
            logger.info(f"Using job profile details for position: {job_profile_details.get('title', job_title)}")
            # Get experience range - support both min_experience/max_experience and min_year/max_year
            min_exp = job_profile_details.get('min_experience') or job_profile_details.get('min_year', 0)
            max_exp = job_profile_details.get('max_experience') or job_profile_details.get('max_year', 0)
            
            profile_info = [
                f"Position: {job_profile_details.get('title', job_title)}",
                f"Description: {job_profile_details.get('job_description', '')}",
                f"Experience: {min_exp}-{max_exp} years",
                f"Qualifications: {job_profile_details.get('qualification', '')}",
                f"Location: {job_profile_details.get('location', '')}"
            ]
            context_parts.append(f"Job Profile:\n" + "\n".join(profile_info))
        elif job_title or job_keywords:
            job_context = f"Job Context: Position '{job_title}', Keywords: {job_keywords}"
            # Add experience requirements if provided (when job_profile_details is not present)
            if min_experience is not None and max_experience is not None:
                job_context += f"\nRequired Experience: {min_experience}-{max_experience} years"
            context_parts.append(job_context)

        # Construct user message with context
        user_message = "Parse the resume from the text and calculate job matching score.\n\n"
        if context_parts:
            user_message += "\n\n".join(context_parts) + "\n\n"
        user_message += "Return JSON with 'parsed_resume' and 'extracted_text' fields."

        # Prepare API call
        headers = {
            "Authorization": f"Bearer {llm_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": RESUME_PARSER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 8192,  # Increased to prevent truncation of JSON response
            "response_format": {"type": "json_object"}
        }

        api_url = f"{llm_base_url}/chat/completions"
        logger.info(f"Completion API call starting to: {api_url}")
        
        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=180)
        response.raise_for_status()

        try:
            resp_json = response.json()
            logger.info(f"Response from resume parser API received")
            
            # Check if response was truncated
            finish_reason = resp_json["choices"][0].get("finish_reason", "unknown")
            logger.info(f"API response finish_reason: {finish_reason}")
            
            if finish_reason == "length":
                logger.warning(f"API response was truncated due to max_tokens limit. Consider increasing max_tokens or reducing input text.")
            
            content = resp_json["choices"][0]["message"]["content"]
            logger.debug(f"Content from resume parser API (first 500 chars): {content[:500]}...")
            logger.info(f"Total content length: {len(content)} characters")
            
            # Try to parse the JSON content
            try:
                result = json.loads(content)
                logger.info(f"Successfully parsed resume data")
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing failed: {str(json_err)}")
                logger.error(f"Problematic content length: {len(content)} characters")
                logger.error(f"Content around error position (if available): {content[max(0, json_err.pos-100):min(len(content), json_err.pos+100)]}")
                
                # Try to fix common JSON issues
                try:
                    # Remove any trailing commas, fix common issues
                    fixed_content = content.strip()
                    if not fixed_content.endswith('}'):
                        # Try to find the last valid closing brace
                        last_brace = fixed_content.rfind('}')
                        if last_brace > 0:
                            fixed_content = fixed_content[:last_brace+1]
                            logger.info(f"Attempting to parse truncated JSON")
                            result = json.loads(fixed_content)
                            logger.info(f"Successfully parsed after truncation")
                        else:
                            raise json_err
                    else:
                        raise json_err
                except Exception as fix_err:
                    logger.error(f"JSON repair attempt failed: {str(fix_err)}")
                    # Log more details for debugging
                    logger.error(f"Full content preview (first 1000 chars): {content[:1000]}")
                    logger.error(f"Full content preview (last 1000 chars): {content[-1000:]}")
                    return {"status": "error", "message": f"Invalid JSON in API response: {str(json_err)}"}
                    
        except KeyError as e:
            logger.error(f"Failed to extract content from API response: {str(e)}")
            logger.error(f"Response structure: {resp_json}")
            return {"status": "error", "message": "Invalid API response structure"}

        # Extract all required fields from the result
        parsed_resume = result.get("parsed_resume", {})
        extracted_text_result = result.get("extracted_text", extracted_text)
        
        # Extract job matching information from personal_info section
        personal_info = parsed_resume.get("personal_info", {})
        job_matching_percentage = personal_info.get("job_matching_percentage", 0)
        job_matching_percentage_reason = personal_info.get("job_matching_percentage_reason", [])
        
        # Legacy fields for backward compatibility
        best_matched_jd_id = result.get("best_matched_jd_id", None)
        best_matched_jd_name = result.get("best_matched_jd_name", None)
        other_matching_jobs = result.get("other_matching_jobs", [])
        matching_percentage_email_flow = result.get("matching_percentage_email_flow", None)
        resume_meta_data = result.get("resume_meta_data", {})

        response = {
            "status": "success",
            "message": "Resume parsed successfully",
            "data": {
                "parsed_resume": parsed_resume,
                "extracted_text": extracted_text_result,
                "job_matching_percentage": job_matching_percentage,
                "job_matching_percentage_reason": job_matching_percentage_reason,
                "best_matched_jd_id": best_matched_jd_id,
                "best_matched_jd_name": best_matched_jd_name,
                "other_matching_jobs": other_matching_jobs,
                "matching_percentage_email_flow": matching_percentage_email_flow,
                "resume_meta_data": resume_meta_data
            },
            "user_id": session_id,
            "session_id": session_id
        }
        logger.info(f"Response from resume parser API: {response}")
        return response

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {str(e)}")
        if e.response.status_code == 413:
            return {
                "status": "error",
                "message": "Text data too large for API. Try a shorter resume."
            }
        try:
            error_message = e.response.json().get("error", str(e))
        except json.JSONDecodeError:
            error_message = str(e)
        return {"status": "error", "message": f"API error: {error_message}"}
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out")
        return {"status": "error", "message": "API request timed out. Try again."}
    except (ValueError, requests.exceptions.RequestException) as e:
        logger.error(f"Error processing resume: {str(e)}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"status": "error", "message": "Failed to process resume text"}


async def _process_resume_with_text_completion(
    job_applicant_id: str,
    extracted_text: str,
    applied_job_title: str,
    applied_job_keywords: list,
    job_applicant_filled_qna: list,
    evaluation_criteria: list,
    job_profile_details: dict,
    min_experience: int,
    max_experience: int,
    llm_key: str,
    llm_base_url: str,
    model: str,
    session_id: str,
    company_id: str = None,
    origin: str = None,
    resume_parser_access_token: str = None,
    include_evaluation: bool = True
):
    """
    Background task to perform full text-based resume parsing using completion API.
    
    Args:
        include_evaluation: If True, sends evaluation_report format to API. If False, sends flattened format.
    """
    try:
        logger.info(f"Starting background text processing for job_applicant_id: {job_applicant_id}")
        logger.info(f"Token: {resume_parser_access_token}")

        if not extracted_text or not extracted_text.strip():
            logger.error(f"No text provided for processing")
            return

        # Step 2: Run the completion API call for full processing
        logger.info(f"Running AI text analysis on resume...")
            
        completion_result = await asyncio.to_thread(
            _analyze_resume_with_text_completion,
            extracted_text,
            job_applicant_id,
            session_id,
            applied_job_title,
            applied_job_keywords,
            job_applicant_filled_qna,
            evaluation_criteria,
            job_profile_details,
            min_experience,
            max_experience,
            llm_key,
            llm_base_url,
            model
        )
        
        if completion_result["status"] == "success":
            logger.info(f"Background text processing completed successfully for job_applicant_id: {job_applicant_id}")
            
            # Extract full data from completion processing
            completion_data = completion_result.get("data", {})
            parsed_resume = completion_data.get("parsed_resume", {})
            
            # Normalize job matching percentage with fallback to 0
            raw_job_matching_percentage = parsed_resume.get("job_matching_percentage")
            job_matching_percentage = normalize_job_matching_percentage(raw_job_matching_percentage)
            if raw_job_matching_percentage != job_matching_percentage:
                logger.info(f"Job matching percentage normalized from {raw_job_matching_percentage} to {job_matching_percentage}")
            
            best_matched_jd_id = completion_data.get("best_matched_jd_id")
            best_matched_jd_name = completion_data.get("best_matched_jd_name")
            other_matching_jobs = completion_data.get("other_matching_jobs", [])
            
            # Normalize email flow matching percentage with fallback to 0
            raw_matching_percentage_email_flow = completion_data.get("matching_percentage_email_flow")
            matching_percentage_email_flow = normalize_job_matching_percentage(raw_matching_percentage_email_flow)
            if raw_matching_percentage_email_flow != matching_percentage_email_flow:
                logger.info(f"Email flow matching percentage normalized from {raw_matching_percentage_email_flow} to {matching_percentage_email_flow}")
            
            # Log parsed data summary
            personal_info = parsed_resume.get("personal_info", {})
            summary_message = f"Resume parsed successfully. Job match: {job_matching_percentage}%"
            if personal_info.get("first_name") and personal_info.get("last_name"):
                summary_message += f" for {personal_info['first_name']} {personal_info['last_name']}"
            logger.info(summary_message)
            
            # Create standardized full response format
            full_response = create_standard_response_format(
                essential_details=None,  # Will use defaults from vision processing
                extracted_text=extracted_text,
                parsed_resume_data=parsed_resume,
                session_id=session_id,
                user_id=job_applicant_id,  # Using job_applicant_id as user_id
                job_matching_percentage=job_matching_percentage,
                best_matched_jd_id=best_matched_jd_id,
                best_matched_jd_name=best_matched_jd_name,
                other_matching_jobs=other_matching_jobs,
                matching_percentage_email_flow=matching_percentage_email_flow,
                is_initial_response=False
            )
            # Format job matching percentage for logging (always show as percentage since we normalize to 0)
            logger.info(f"Full parsing results - Job matching: {job_matching_percentage}%")
            logger.info(f"Complete standardized response ready for update API")
            
            # Call the update API to store the full parsing results
            if company_id and resume_parser_access_token:
                try:
                    await call_update_job_applicant_api(
                        company_id=company_id,
                        job_applicant_id=job_applicant_id,
                        parsed_resume_data=parsed_resume,
                        extracted_text=extracted_text,
                        resume_parser_access_token=resume_parser_access_token,
                        origin=origin,
                        session_id=session_id,
                        is_evaluation_report=include_evaluation,
                        job_matching_percentage=job_matching_percentage,
                        matching_percentage_email_flow=matching_percentage_email_flow
                    )
                    if include_evaluation:
                        logger.info(f"Successfully updated job applicant via API with evaluation_report format")
                    else:
                        logger.info(f"Successfully updated job applicant via API with flattened format")
                    logger.info(f"Resume parsing completed successfully! Job match: {job_matching_percentage}%")
                        
                except Exception as api_error:
                    logger.error(f"Failed to update job applicant via API: {str(api_error)}")
            else:
                logger.warning(f"Missing required parameters for API update: company_id={company_id}, token_available={bool(resume_parser_access_token)}")
            
            
        else:
            logger.error(f"Background text processing failed for job_applicant_id: {job_applicant_id}, error: {completion_result.get('message')}")
            
    except Exception as e:
        logger.error(f"Error in background text processing for job_applicant_id: {job_applicant_id}, error: {str(e)}")


async def initiate_resume_parser_agent(
    job_applicant_id: str,
    resume_url: str,
    resume_text: str = None,
    applied_job_title: str = None,
    applied_job_keywords: list[str] = None,
    evaluation_criteria: list = None,
    job_profile_details: dict = None,
    job_applicant_filled_qna: list = None,
    min_experience: int = None,
    max_experience: int = None,
    llm_key: str = None,
    llm_base_url: str = None,
    model: str = None,
    company_id: str = None,
    origin: str = None,
    resume_parser_access_token: str = None,
    rails_api_url: str = None,
    enable_real_time_updates: bool = False,
    resume_parsing: bool = True,
    evaluation_result: bool = False
) -> dict:
    """
    Parse resume from URL and optionally run background evaluation.
    
    Args:
        job_applicant_id (str): Job applicant ID for tracking
        resume_url (str): URL to the resume file (PDF/DOC/DOCX)
        resume_text (str, optional): Pre-extracted resume text to skip parsing
        applied_job_title (str, optional): Job title applied for
        applied_job_keywords (list[str], optional): Keywords for job matching
        job_applicant_filled_qna (list, optional): Pre-filled QNA data
        llm_key (str, optional): LLM API key
        llm_base_url (str, optional): LLM base URL
        model (str, optional): LLM model name
        company_id (str, optional): Company ID for API calls
        origin (str, optional): Origin domain for API calls
        resume_parser_access_token (str, optional): Access token for Rails API
        rails_api_url (str, optional): Kept for backward compatibility (not used)
        enable_real_time_updates (bool, optional): Kept for backward compatibility (not used)
        resume_parsing (bool, optional): Control whether to parse resume contents. Default True.
        evaluation_result (bool, optional): Control whether to include evaluation report. Default False.
                                           If True, triggers background job for full evaluation.
        
    Returns:
        dict: Parsing results with status and extracted data
        
    Note:
        - When resume_parsing=True and evaluation_result=False: Returns only parsed resume contents
        - When resume_parsing=True and evaluation_result=True: Returns parsed resume + evaluation report
        - When resume_parsing=False and evaluation_result=True with resume_text provided: Uses provided text for evaluation only
    """
    session_id = f"ka_session_{uuid.uuid4().hex}"
    user_id = f"ka_user_{uuid.uuid4().hex}"
    logger.info(f"{session_id} {user_id} - initiate_resume_parser_agent - resume_parsing: {resume_parsing}, evaluation_result: {evaluation_result}, resume_text_provided: {bool(resume_text and resume_text.strip())}")
    
    try:
        # Early return if both resume_parsing and evaluation_result are False
        if not resume_parsing and not evaluation_result:
            logger.info(f"Both resume_parsing and evaluation_result are False. Skipping all operations.")
            return {
                "status": "success",
                "message": "Resume parsing and evaluation have been disabled. No operations were performed as both resume_parsing and evaluation_result flags are set to false.",
                "data": {
                    "parsed_resume": {},
                    "extracted_text": "",
                    "job_matching_percentage": 0,
                    "matching_percentage_email_flow": 0
                },
                "user_id": user_id,
                "session_id": session_id,
                "parsing_skipped": True,
                "evaluation_skipped": True
            }
        
        # Check if resume_text is provided when resume_parsing=False and evaluation_result=True
        if not resume_parsing and evaluation_result and resume_text and resume_text.strip():
            logger.info(f"Using provided resume_text for evaluation (resume_parsing=False, evaluation_result=True)")
            extracted_text = resume_text.strip()
            logger.info(f"Running evaluation synchronously - NO API update, returning full evaluation immediately")
            
            # Run evaluation synchronously (NO background processing, NO API update)
            completion_result = await asyncio.to_thread(
                _analyze_resume_with_text_completion,
                extracted_text,
                job_applicant_id or "eval_only",
                session_id,
                applied_job_title,
                applied_job_keywords,
                job_applicant_filled_qna,
                evaluation_criteria,
                job_profile_details,
                min_experience,
                max_experience,
                llm_key,
                llm_base_url,
                model
            )
            
            if completion_result["status"] == "success":
                completion_data = completion_result.get("data", {})
                parsed_resume = completion_data.get("parsed_resume", {})
                
                # Normalize job matching percentage
                job_matching_percentage = normalize_job_matching_percentage(
                    completion_data.get("job_matching_percentage")
                )
                matching_percentage_email_flow = normalize_job_matching_percentage(
                    completion_data.get("matching_percentage_email_flow")
                )
                
                logger.info(f"Evaluation completed successfully with job matching: {job_matching_percentage}% - NO API update")
                logger.info(f"Excluding extracted_text from response (resume_parsing=False, evaluation_result=True with provided text)")
                
                # Return full evaluation data immediately (NO API update)
                # Do NOT include extracted_text since client already has it
                return create_standard_response_format(
                    essential_details=None,
                    extracted_text="",  # Empty - client already provided the text
                    parsed_resume_data=parsed_resume,
                    session_id=session_id,
                    user_id=user_id,
                    job_matching_percentage=job_matching_percentage,
                    best_matched_jd_id=completion_data.get("best_matched_jd_id"),
                    best_matched_jd_name=completion_data.get("best_matched_jd_name"),
                    other_matching_jobs=completion_data.get("other_matching_jobs", []),
                    matching_percentage_email_flow=matching_percentage_email_flow,
                    is_initial_response=False
                )
            else:
                logger.error(f"Evaluation failed: {completion_result.get('message')}")
                return {
                    "status": "error",
                    "message": completion_result.get("message", "Evaluation failed"),
                    "user_id": user_id,
                    "session_id": session_id
                }
        
        # Check if resume_text is not provided but evaluation is requested with resume_parsing=False
        if not resume_parsing and evaluation_result and (not resume_text or not resume_text.strip()):
            logger.warning(f"resume_parsing=False and evaluation_result=True but resume_text is empty. Will parse resume from URL.")
            # Fall through to normal parsing flow
        
        logger.info(f"Starting resume parsing process")
        
        logger.info(f"Processing resume from URL: {resume_url}")

        # Step 1: Download and extract text from resume file
        logger.info(f"Downloading and extracting text from resume...")
            
        text_result = await asyncio.to_thread(process_resume_file, resume_url, session_id)
        if text_result["status"] != "success":
            logger.error(f"Failed to process resume file: {text_result['message']}")
            return {
                "status": "error",
                "message": text_result["message"],
                "user_id": user_id,
                "session_id": session_id
            }
        
        # Extract text from the processing operation
        extracted_text = text_result["data"].get("extracted_text", "")
        logger.info(f"Resume text extracted successfully, extracting essential details...")
        
        # Step 2: Extract essential details from already extracted text (fast operation)
        essential_result = await extract_essential_details_from_text(
            extracted_text=extracted_text,
            llm_key=llm_key,
            llm_base_url=llm_base_url,
            model=model,
            session_id=session_id
        )
        
        if essential_result.get("status") == "error":
            logger.error(f"Failed to extract essential details: {essential_result.get('message')}")
            return {
                "status": "error",
                "message": essential_result.get("message"),
                "user_id": user_id,
                "session_id": session_id
            }
        # Use the access token from the function parameter, fallback to default if needed
        effective_access_token = resume_parser_access_token
        
        # Step 3: Determine if we should do full parsing and API update
        should_update_api = (
            _is_valid_param(job_applicant_id) and 
            _is_valid_param(effective_access_token)
        )
        
        # Determine if we need background processing
        will_process_in_background = should_update_api  # Always use background if we have valid credentials
        
        if will_process_in_background:
            if evaluation_result:
                # Case 1: resume_parsing=True and evaluation_result=True 
                # -> Do full parsing + evaluation in background, return essential details immediately
                logger.info(f"Will process in background - Essential details extracted (PARTIAL) - Full parsing with evaluation in progress...")
            else:
                # Case 2: resume_parsing=True and evaluation_result=False
                # -> Do full parsing (no evaluation) in background, return essential details immediately
                logger.info(f"Will process in background - Essential details extracted (PARTIAL) - Full parsing without evaluation in progress...")
            
            # Start background task with full parsing + API update (with or without evaluation)
            asyncio.create_task(_process_resume_with_text_completion(
                job_applicant_id=job_applicant_id,
                extracted_text=extracted_text,
                applied_job_title=applied_job_title,
                applied_job_keywords=applied_job_keywords,
                job_applicant_filled_qna=job_applicant_filled_qna,
                evaluation_criteria=evaluation_criteria,
                job_profile_details=job_profile_details,
                min_experience=min_experience,
                max_experience=max_experience,
                llm_key=llm_key,
                llm_base_url=llm_base_url,
                model=model,
                session_id=session_id,
                company_id=company_id,
                origin=origin,
                resume_parser_access_token=effective_access_token,
                include_evaluation=evaluation_result
            ))
            
            if evaluation_result:
                logger.info(f"Essential details extracted, full parsing + evaluation and API update started in background for applicant {job_applicant_id}")
            else:
                logger.info(f"Essential details extracted, full parsing (no evaluation) and API update started in background for applicant {job_applicant_id}")
        
        # Case 3: Missing required parameters for API update
        else:
            skip_reasons = []
            if not _is_valid_param(job_applicant_id):
                skip_reasons.append("job_applicant_id missing")
            if not _is_valid_param(effective_access_token):
                skip_reasons.append("resume_parser_access_token missing")
            
            logger.info(f"Skipping background processing and API update - Reasons: {', '.join(skip_reasons)}")
        
        # Step 4: Return standardized response format immediately
        response = create_standard_response_format(
            essential_details=essential_result["data"],
            extracted_text=extracted_text,
            session_id=session_id,
            user_id=user_id,
            is_initial_response=True
        )
        
        # Add flag to indicate this is partial completion when background processing is happening
        if will_process_in_background:
            response["status"] = "partial"  # Override status to partial
            response["partial_completion"] = True
            response["background_processing"] = True
            response["processing_status"] = "in_progress"  # Explicit processing status
            response["completion_status"] = "partial"     # Explicit completion status
            response["prevent_completion_log"] = True     # Flag for Rails to NOT send completed
            
            if evaluation_result:
                response["message"] = "Essential details extracted (PARTIAL) - Full parsing with evaluation in progress"
            else:
                response["message"] = "Essential details extracted (PARTIAL) - Full parsing without evaluation in progress"
            
        return response
        
    except Exception as e:
        logger.error(f"Error in resume parser: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "data": {},
            "user_id": user_id,
            "session_id": session_id
        }