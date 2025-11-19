import os
import time
import jwt
import json
import requests
import re
import base64  # Added for token masking
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

from app.utils.logger import logger
from app.services.s3_service import s3_service
from pathlib import Path

load_dotenv('.env')

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_SECRET = os.getenv("SLACK_BOT_SECRET")  # Shared secret for signing JWT
HRMS_API_URL = os.getenv("HRMS_AGENT")
TOKEN_STORE_FILE = "tokens.json"
TOKEN_EXPIRY_SECONDS = 24 * 3600  # 24 hours
RAILS_API_URL = f"{os.getenv('KIVO_API_BASE_URL_SLACK')}api/v1/companies/{os.getenv('COMPANY_ID')}/fetch_user_by_email"

# Helper functions for token masking
def mask_token(token: str) -> str:
    """Mask a token for logging (show first 4 and last 4 characters, rest as asterisks)."""
    if not token:
        return "None"
    if len(token) < 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"

def encode_token(token: str) -> str:
    """Encode token for storage using base64."""
    return base64.b64encode(token.encode()).decode()

def decode_token(encoded_token: str) -> str:
    """Decode base64-encoded token for use."""
    return base64.b64decode(encoded_token.encode()).decode()

def validate_env_vars():
    # Mask SLACK_BOT_TOKEN and SLACK_BOT_SECRET in logs
    logger.info(
        f"Starting Slack Bot with tokens: "
        f"SLACK_BOT_TOKEN set: {bool(SLACK_BOT_TOKEN)}, "
        f"SLACK_APP_TOKEN set: {bool(SLACK_APP_TOKEN)}, "
        f"SLACK_BOT_SECRET set: {bool(SLACK_BOT_SECRET)}"
    )
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN or not SLACK_BOT_SECRET:
        logger.error("Missing SLACK_BOT_TOKEN, SLACK_APP_TOKEN or SLACK_BOT_SECRET in environment")
        raise ValueError("Missing SLACK_BOT_TOKEN, SLACK_APP_TOKEN or SLACK_BOT_SECRET in environment")

def load_tokens():
    logger.debug("Loading tokens from file...")
    if not os.path.exists(TOKEN_STORE_FILE):
        logger.warning("Token file does not exist.")
        return {}
    try:
        with open(TOKEN_STORE_FILE, "r") as f:
            encoded_tokens = json.load(f)
            # Decode tokens when loading
            tokens = {
                user_id: {
                    "auth_token": decode_token(token_info["auth_token"]),
                    "timestamp": token_info["timestamp"]
                }
                for user_id, token_info in encoded_tokens.items()
            }
            logger.debug(f"Loaded tokens (masked): { {k: {'auth_token': mask_token(v['auth_token']), 'timestamp': v['timestamp']} for k, v in tokens.items()} }")
            return tokens
    except Exception as e:
        logger.error(f"Error loading tokens file: {e}")
        return {}

def save_tokens(tokens):
    # Encode tokens before saving
    encoded_tokens = {
        user_id: {
            "auth_token": encode_token(token_info["auth_token"]),
            "timestamp": token_info["timestamp"]
        }
        for user_id, token_info in tokens.items()
    }
    logger.debug(f"Saving tokens (masked): { {k: {'auth_token': mask_token(decode_token(v['auth_token'])), 'timestamp': v['timestamp']} for k, v in encoded_tokens.items()} }")
    try:
        with open(TOKEN_STORE_FILE, "w") as f:
            json.dump(encoded_tokens, f)
        logger.info("Tokens saved successfully.")
    except Exception as e:
        logger.error(f"Error saving tokens file: {e}")

def is_token_valid(token_info):
    logger.debug(f"Checking token validity for: {token_info}")
    if not token_info:
        logger.warning("Token info is None or empty.")
        return False
    stored_time = token_info.get("timestamp", 0)
    valid = (time.time() - stored_time) < TOKEN_EXPIRY_SECONDS
    logger.debug(f"Token valid: {valid}")
    return valid

def generate_jwt_token(email: str, secret: str, expire_seconds=60):
    logger.debug(f"Generating JWT token for email: {email} with expiry {expire_seconds}s")
    payload = {
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + expire_seconds,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    logger.debug(f"Generated JWT token (masked): {mask_token(token)}")
    return token

def get_user_email(client, user_id):
    logger.debug(f"Fetching email for user ID: {user_id}")
    try:
        result = client.users_info(user=user_id)
        if result.get("ok"):
            profile = result["user"].get("profile", {})
            email = profile.get("email")
            logger.debug(f"Found email: {email}")
            return email
        else:
            logger.warning(f"Slack API returned not ok: {result}")
    except Exception as e:
        logger.error(f"Failed to get email for user {user_id}: {e}")
    return None

def format_slack_message(text: str) -> str:
    """
    Convert markdown-like text to Slack formatting:
    - Convert **bold** to *bold*
    - Convert *italic* to _italic_
    - Convert ~~strikethrough~~ to ~strikethrough~
    - Convert bullets (- or *) to Slack bullets (•)
    - Remove emojis
    """
    emoji_pattern = re.compile("[\U0001F600-\U0001F64F"
                               "\U0001F300-\U0001F5FF"
                               "\U0001F680-\U0001F6FF"
                               "\U0001F1E0-\U0001F1FF]+", flags=re.UNICODE)
    text = emoji_pattern.sub("", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*]\s+", line):
            lines[i] = "• " + re.sub(r"^\s*[-*]\s+", "", line)
    text = "\n".join(lines)
    return text.strip()

app = App(token=SLACK_BOT_TOKEN)


def _process_message_or_file(message, say, client):
    """Unified handler for plain text messages and file shares (voice notes)."""
    logger.debug(f"Processing message payload ==> {message}")
    user_id = message.get("user")
    if not user_id:
        logger.warning("User ID missing in message.")
        return

    # If a file is shared (e.g., Slack voice note), handle upload to S3 and forward to HRMS
    try:
        files = message.get("files", []) or []
        if files:
            logger.info(f"Detected {len(files)} file(s) attached to the message. Starting download pipeline…")
            # 1) Prefer audio file, but collect all images
            target_audio = None
            image_files = []
            for f in files:
                mimetype = f.get("mimetype", "") or ""
                subtype = f.get("subtype", "") or ""
                if not target_audio and (mimetype.startswith("audio/") or subtype == "slack_audio"):
                    target_audio = f
                if mimetype.startswith("image/"):
                    image_files.append(f)

            if target_audio:
                # Handle audio upload to S3
                media = target_audio
                file_id = media.get("id")
                file_name = media.get("name") or media.get("title") or f"slack_file_{int(time.time())}"
                url_private = media.get("url_private_download") or media.get("url_private")
                mimetype = media.get("mimetype", "audio/mp4")
                pretty_type = media.get("pretty_type")
                duration_ms = media.get("duration_ms")
                logger.info(f"Audio file found: id={file_id}, name={file_name}, type={mimetype}, pretty_type={pretty_type}, duration_ms={duration_ms}")

                if not url_private:
                    logger.error("Audio file is missing url_private/url_private_download; cannot download.")
                    say("Couldn't access the audio file. Please try again or upload again.")
                    return

                # Derive extension
                ext = mimetype.split("/")[-1] if "/" in mimetype else (Path(file_name).suffix.lstrip(".") or "mp4")
                safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file_name)
                object_name = f"slack_{file_id}_{safe_name}"
                if not object_name.lower().endswith(f".{ext}"):
                    object_name = f"{object_name}.{ext}"

                headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Accept": "*/*", "User-Agent": "kivo-slack-bot/1.0"}
                try:
                    logger.info("Downloading Slack audio into memory for direct S3 upload")
                    resp = requests.get(url_private, headers=headers, timeout=180, stream=True)
                    logger.debug(f"Slack audio GET status: {resp.status_code}")
                    if resp.status_code >= 400:
                        try:
                            logger.error(f"Slack GET error body: {resp.text}")
                        except Exception:
                            pass
                    resp.raise_for_status()
                    content_chunks = []
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            content_chunks.append(chunk)
                    file_bytes = b"".join(content_chunks)
                    logger.info(f"Downloaded {len(file_bytes)} bytes from Slack (audio)")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to download Slack audio file: {e}")
                    say("I couldn't download the audio from Slack. Please try again.")
                    return

                try:
                    timestamp = int(time.time())
                    object_key = f"voice_notes/{user_id}/{timestamp}_{object_name}"
                    logger.info(f"Uploading audio bytes to S3 at key: {object_key}")
                    s3_url = s3_service.upload_bytes(file_bytes, object_key, content_type=mimetype)
                    logger.info(f"Uploaded to S3 successfully: {s3_url}")
                except Exception as e:
                    logger.error(f"S3 upload failed (audio): {e}")
                    say("I downloaded the audio but failed to upload to storage. Please try again.")
                    return

                message["_voice_note_s3_url"] = s3_url
                message["_voice_note_mimetype"] = mimetype
                logger.info("Voice note prepared; proceeding to HRMS API call with input_mode=voice_note.")

            elif image_files:
                # Handle one or more image uploads to S3
                image_s3_urls = []
                for media in image_files:
                    try:
                        file_id = media.get("id")
                        file_name = media.get("name") or media.get("title") or f"slack_image_{int(time.time())}"
                        url_private = media.get("url_private_download") or media.get("url_private")
                        mimetype = media.get("mimetype", "image/jpeg")
                        logger.info(f"Image file found: id={file_id}, name={file_name}, type={mimetype}")

                        if not url_private:
                            logger.error("Image file is missing url_private/url_private_download; cannot download.")
                            continue

                        ext = mimetype.split("/")[-1] if "/" in mimetype else (Path(file_name).suffix.lstrip(".") or "jpg")
                        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file_name)
                        object_name = f"slack_{file_id}_{safe_name}"
                        if not object_name.lower().endswith(f".{ext}"):
                            object_name = f"{object_name}.{ext}"

                        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Accept": "*/*", "User-Agent": "kivo-slack-bot/1.0"}
                        try:
                            logger.info("Downloading Slack image into memory for direct S3 upload")
                            resp = requests.get(url_private, headers=headers, timeout=180, stream=True)
                            logger.debug(f"Slack image GET status: {resp.status_code}")
                            if resp.status_code >= 400:
                                try:
                                    logger.error(f"Slack GET error body: {resp.text}")
                                except Exception:
                                    pass
                            resp.raise_for_status()
                            content_chunks = []
                            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    content_chunks.append(chunk)
                            file_bytes = b"".join(content_chunks)
                            logger.info(f"Downloaded {len(file_bytes)} bytes from Slack (image)")
                        except requests.exceptions.RequestException as e:
                            logger.error(f"Failed to download Slack image file: {e}")
                            continue

                        try:
                            timestamp = int(time.time())
                            object_key = f"image_uploads/{user_id}/{timestamp}_{object_name}"
                            logger.info(f"Uploading image bytes to S3 at key: {object_key}")
                            s3_url = s3_service.upload_bytes(file_bytes, object_key, content_type=mimetype)
                            logger.info(f"Uploaded to S3 successfully: {s3_url}")
                            image_s3_urls.append(s3_url)
                        except Exception as e:
                            logger.error(f"S3 upload failed (image): {e}")
                            continue
                    except Exception as inner_e:
                        logger.error(f"Unexpected error processing an image: {inner_e}")
                        continue

                if not image_s3_urls:
                    say("I couldn't process any of the images you uploaded. Please try again.")
                    return

                message["_image_s3_urls"] = image_s3_urls
                # Maintain backward compatibility with single-image consumers
                message["_image_s3_url"] = image_s3_urls[0]
                logger.info(f"Prepared {len(image_s3_urls)} image(s); proceeding to HRMS API call with input_mode=image.")
            else:
                logger.info("No audio/image attachments handled; proceeding with text handling.")
    except Exception as e:
        logger.error(f"Error during Slack file processing: {e}")

    # From here on, follow the same flow as text handling
    max_retries = 3
    delay = 1
    email = None

    for attempt in range(max_retries):
        logger.debug(f"Attempt count to fetch email {attempt+1}")
        email = get_user_email(client, user_id)
        if email:
            break
        logger.debug(f"Email not found for user {user_id}. Retrying... ({attempt+1}/{max_retries})")
        time.sleep(delay)

    if not email:
        say("Could not fetch your Slack email. Please update your profile and try again.")
        logger.warning(f"Email not found for user {user_id} after {max_retries} retries")
        return

    logger.info(f"Processing your request for email: {email}")

    # Generate session ID based on thread timestamp to separate conversations
    thread_ts = message.get("thread_ts") or time.time()
    session_id_for_api = f"{email}_{thread_ts}"
    logger.info(f"Using session ID: {session_id_for_api}")

    tokens = load_tokens()
    token_info = tokens.get(user_id)

    if is_token_valid(token_info):
        auth_token = token_info["auth_token"]
        logger.info(f"Using cached authentication token (masked): {mask_token(auth_token)}")
    else:
        logger.info("No valid cached token found, fetching new one from Rails API.")
        jwt_token = generate_jwt_token(email, SLACK_BOT_SECRET)

        rails_headers = {
            "Content-Type": "application/json",
            "X-Slack-Auth-Token": jwt_token,
        }

        rails_payload = {"email": email}

        try:
            logger.debug(f"Calling Rails API {RAILS_API_URL} with payload: {rails_payload} and headers: {{'Content-Type': 'application/json', 'X-Slack-Auth-Token': '{mask_token(jwt_token)}'}}")
            rails_resp = requests.post(RAILS_API_URL, json=rails_payload, headers=rails_headers, timeout=30)
            logger.info(f"Rails API response status: {rails_resp.status_code}")
            rails_resp.raise_for_status()
            rails_data = rails_resp.json()
            logger.debug(f"Rails API response JSON: {rails_data}")

            if not rails_data.get("success"):
                logger.error(f"Rails API indicated failure: {rails_data.get('message')}")
                return

            auth_token = rails_data.get("authorization", {}).get("token")
            if not auth_token:
                logger.error("Authorization token missing in Rails API response.")
                return

            tokens[user_id] = {
                "auth_token": auth_token,
                "timestamp": time.time(),
            }
            save_tokens(tokens)

        except requests.exceptions.RequestException as e:
            logger.error(f"Requests exception: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected exception: {e}")
            return

    try:
        hrms_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
            "X-Origin-Service": os.getenv('KIVO_API_BASE_URL_SLACK'),
            "X-Request-Mode": "slack"
        }

        print("hrms_headers:",hrms_headers)

        processed_text = replace_mentions_with_display_names(client, message.get("text", ""))
        voice_s3_url = message.get("_voice_note_s3_url")
        image_s3_url = message.get("_image_s3_url")
        image_s3_urls = message.get("_image_s3_urls")
        
        # Handle different combinations of text, voice, and image
        if voice_s3_url:
            # Text message + voice URL
            hrms_payload = {
                "query": processed_text or "",
                "query_id": session_id_for_api,
                "input_mode": "voice_note",
                "input_data_url": voice_s3_url,
            }
            logger.info("Submitting HRMS request in voice_note mode with input_data_url.")
        elif image_s3_urls:
            # Text message + multiple image URLs
            input_data_value = image_s3_urls if len(image_s3_urls) > 1 else image_s3_urls[0]
            hrms_payload = {
                "query": processed_text or "",
                "query_id": session_id_for_api,
                "input_mode": "image",
                "input_data_url": input_data_value,
            }
            logger.info(
                "Submitting HRMS request in image mode with {}.".format(
                    "list of input_data_url(s)" if isinstance(input_data_value, list) else "single input_data_url"
                )
            )
        else:
            # Only text
            hrms_payload = {
                "query": processed_text,
                "query_id": session_id_for_api,
            }

        logger.debug(f"Calling HRMS API {HRMS_API_URL} with payload: {hrms_payload} and headers: {{'Content-Type': 'application/json', 'Authorization': 'Bearer {mask_token(auth_token)}'}}")
        if email:
            hrms_resp = requests.post(HRMS_API_URL, json=hrms_payload, headers=hrms_headers, timeout=90)
        logger.info(f"HRMS API response status: {hrms_resp.status_code}")

        if hrms_resp.status_code == 403:
            logger.error("Access forbidden: The user does not have permission for this action.")
            say("You are not authorized to perform this action. Please contact your admin.")
            return
        if hrms_resp.status_code == 204:
            logger.info("HRMS API returned 204 No Content. No response to be sent.")
            return
        
        hrms_resp.raise_for_status()
        hrms_data = hrms_resp.json()
        logger.debug(f"HRMS API response JSON: {hrms_data}")

        if hrms_data.get("status") and hrms_data.get("response"):
            formatted_response = format_slack_message(hrms_data["response"])
            say(formatted_response)
        else:
            say("HRMS API did not return a valid response.")
            logger.error("Invalid response from HRMS API.")

    except requests.exceptions.RequestException as e:
        say(f"Slight delay in connection. Hang tight and try again please.")
        logger.error(f"HRMS requests exception: {e}")
    except Exception as e:
        say(f"Slight delay in connection. Hang tight and try again please.")
        logger.error(f"HRMS unexpected exception: {e}")

@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    user_id = event["user"]
    try:
        home_view = {
            "type": "home",
            "blocks": [
                {
                    "type": "image",
                    "image_url": "https://www.kivo.ai/production/assets/landing/kivo-nav-logo-9fe4fd56a11af68787043d05df0e4da10abd4d890d65c50f8aef4345ccd3b37b.png",
                    "alt_text": "AI Assistant"
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":wave: Hey <@{user_id}>, welcome back to *Kivo.ai Agent*!  \nYour assistant is ready to simplify tasks and streamline workflows."
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*🚀 Core Features*"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "• Automate routine workflows"},
                        {"type": "mrkdwn", "text": "• Instant AI-powered answers"},
                        {"type": "mrkdwn", "text": "• Scheduling & reminders"},
                        {"type": "mrkdwn", "text": "• Data analysis & reports"},
                        {"type": "mrkdwn", "text": "• Seamless tool integrations"},
                        {"type": "mrkdwn", "text": "• Adaptive learning & insights"}
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*📊 HRMS & Real-Time Data*"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "• Employee profiles & records"},
                        {"type": "mrkdwn", "text": "• Attendance & leave tracking"},
                        {"type": "mrkdwn", "text": "• Work-from-home updates"},
                        {"type": "mrkdwn", "text": "• Payroll summaries & reports"},
                        {"type": "mrkdwn", "text": "• Timely HR alerts & notifications"}
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*📌 HRMS Smart Features*"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "• Apply & approve leaves directly in Slack"},
                        {"type": "mrkdwn", "text": "• Daily attendance check-ins with smart alerts"},
                        {"type": "mrkdwn", "text": "• Work-from-home status and updates"},
                        {"type": "mrkdwn", "text": "• Birthday and anniversary celebrations"},
                        {"type": "mrkdwn", "text": "• Fetch salary slips & payroll summaries"},
                        {"type": "mrkdwn", "text": "• View team hierarchy and manager details"}
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*🤖 Advanced AI & Integrations*"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "• Natural language understanding"},
                        {"type": "mrkdwn", "text": "• CRM, ERP & enterprise tool integration"},
                        {"type": "mrkdwn", "text": "• Data privacy & security"},
                        {"type": "mrkdwn", "text": "• Multilingual support"},
                        {"type": "mrkdwn", "text": "• AI-driven business insights"}
                    ]
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🌐 Visit Kivo.ai"},
                            "url": "https://www.kivo.ai/",
                            "action_id": "visit_kivo",
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "📞 Contact Us"},
                            "url": "https://www.kivo.ai/contact-us",
                            "action_id": "contact_us"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "Learn more at <https://www.kivo.ai/>"}
                    ]
                }
            ]
        }
        client.views_publish(user_id=user_id, view=home_view)
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

def get_user_display_name(client, user_id):
    try:
        result = client.users_info(user=user_id)
        if result.get("ok"):
            profile = result["user"].get("profile", {})
            return profile.get("display_name") or profile.get("real_name") or user_id
    except Exception as e:
        logger.error(f"Failed to get display name for user {user_id}: {e}")
    return user_id

def replace_mentions_with_display_names(client, text):
    mention_pattern = re.compile(r"<@([A-Z0-9]+)>")
    matches = mention_pattern.findall(text)
    for user_id in matches:
        display_name = get_user_display_name(client, user_id)
        text = text.replace(f"<@{user_id}>", display_name)
    return text


@app.message(re.compile(r".*", re.S))
def message_handler(message, say, client):
    # Handle both text and file_share messages here to ensure single, consistent flow
    _process_message_or_file(message, say, client)


# Handle message events with subtype=file_share to avoid "Unhandled request"
@app.event("message")
def handle_message_events(body, say, client, logger):
    event = body.get("event", {})
    subtype = event.get("subtype")
    if subtype == "file_share":
        logger.info("Handling Slack file_share event via event listener")
        _process_message_or_file(event, say, client)
    else:
        # Avoid duplicate handling; text-only is handled by @app.message
        logger.debug(f"Ignoring message event with subtype={subtype}")


# Removed separate event handlers to avoid conflicts with message listener

if __name__ == "__main__":
    validate_env_vars()
    logger.info("Starting Slack bot with Socket Mode Handler...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
