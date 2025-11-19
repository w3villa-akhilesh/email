import imaplib
import email
from email.header import decode_header
import time
import os
import logging
import select
import ssl
from dotenv import load_dotenv
import threading
from resume_forwarder import forward_to_resume_parser
from sqlalchemy.orm import Session
from app.services.my_sql_client import get_engine, create_tables_if_not_exist
from app.models.db_models import EmailInboxConfig
from app.utils.logger import logger

# Load environment variables
load_dotenv()

# IDLE timeout configuration (in seconds)
IDLE_TIMEOUT = 1 * 60  # 1 minute
PING_TIMEOUT = 30      # 30 seconds

def _load_inboxes_from_db():
    try:
        engine = get_engine()
        with Session(engine) as session:
            rows = (
                session.query(EmailInboxConfig)
                .filter(EmailInboxConfig.is_active == True)
                .all()
            )
            return [
                {
                    "account_email": r.account_email,
                    "password": r.password,
                    "imap_server": r.imap_server,
                    "imap_port": r.imap_port,
                    "company_id": r.company_id,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Error loading inboxes from DB: {e}")
        return []

def get_email_accounts():
    """
    Load email inbox configs from DB; fallback to env if none.
    """
    inboxes = _load_inboxes_from_db()
    if inboxes:
        return [
            {
                "account": r["account_email"],
                "password": r["password"],
                "imap_server": r.get("imap_server", "imap.gmail.com"),
                "imap_port": int(r.get("imap_port", 993)),
                "company_id": r.get("company_id")
            }
            for r in inboxes
        ]

    # Fallback
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
    email_accounts = []
    index = 1
    while True:
        email_account = os.getenv(f"EMAIL_ACCOUNT_{index}")
        email_password = os.getenv(f"EMAIL_PASSWORD_{index}")
        if not email_account or not email_password:
            break
        email_accounts.append({
            "account": email_account,
            "password": email_password,
            "imap_server": IMAP_SERVER,
            "imap_port": IMAP_PORT,
            "company_id": os.getenv("COMPANY_ID")
        })
        index += 1
    if not email_accounts:
        email_account = os.getenv("EMAIL_ACCOUNT")
        email_password = os.getenv("EMAIL_PASSWORD")
        if email_account and email_password:
            email_accounts.append({
                "account": email_account,
                "password": email_password,
                "imap_server": IMAP_SERVER,
                "imap_port": IMAP_PORT,
                "company_id": os.getenv("COMPANY_ID")
            })
    return email_accounts

def process_email(msg, company_id: str = None):
    """
    Process and display the email content, body, and attachments.
    """
    # Decode the subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")

    from_ = msg.get("From")
    to_ = msg.get("To")
    date_ = msg.get("Date")

    # Prepare email_content (metadata)
    email_content = {
        "subject": subject,
        "from": from_,
        "to": to_,
        "date": date_
    }

    # Extract the body
    email_body = None
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    email_body = part.get_payload(decode=True)
                    if email_body:
                        email_body = email_body.decode("utf-8", errors="replace")
                        break
                except Exception as e:
                    email_body = f"[Error decoding body: {e}]"
    else:
        try:
            email_body = msg.get_payload(decode=True)
            if email_body:
                email_body = email_body.decode("utf-8", errors="replace")
        except Exception as e:
            email_body = f"[Error decoding body: {e}]"

    # Extract attachments
    email_attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Decode the filename if necessary
                    decoded_filename = decode_header(filename)[0][0]
                    if isinstance(decoded_filename, bytes):
                        decoded_filename = decoded_filename.decode()
                    
                    # Get the attachment content
                    content = part.get_payload(decode=True)
                    
                    email_attachments.append({
                        "filename": decoded_filename,
                        "content_type": part.get_content_type(),
                        "size": len(content) if content else 0,
                        "content": content  # Store the actual content
                    })

    # Log the email details
    logger.info("\nemail_content:")
    logger.info(f"  Subject: {email_content['subject']}")
    logger.info(f"  From: {email_content['from']}")
    logger.info(f"  To: {email_content['to']}")
    logger.info(f"  Date: {email_content['date']}")
    
    logger.info("\nemail_body:")
    logger.info(f"  {email_body if email_body else '[No body content found]'}")
    
    logger.info("\nemail_attachments:")
    if email_attachments:
        for attachment in email_attachments:
            logger.info(f"  - Filename: {attachment['filename']}")
            logger.info(f"    Content-Type: {attachment['content_type']}")
            logger.info(f"    Size: {attachment['size']} bytes")
    else:
        logger.info("  [No attachments found]")

    # Forward all email data to the resume parser agent
    logger.info("Starting to process email")
    logger.debug(f"Decoded subject: {subject}")
    logger.debug(f"Extracted email body: {email_body}")
    logger.debug(f"Extracted {len(email_attachments)} attachments")
    logger.info("Forwarding email data to resume parser")
    forward_to_resume_parser(email_content, email_body, email_attachments, company_id=company_id)

def idle_done(mail, tag, timeout=10):
    """
    Send DONE and read until the server sends the final tagged OK response.
    Ignore any untagged responses (like * 69 FETCH).
    """
    mail.send(b"DONE\r\n")
    tag_str = tag.decode() if isinstance(tag, bytes) else str(tag)
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = mail.readline()
        if not resp:
            time.sleep(0.1)
            continue
        line = resp.decode(errors="ignore").strip()

        # Final tagged response for our IDLE command
        if line.startswith(tag_str):
            return line

        # Ungtagged responses (like * 69 FETCH) -> ignore and keep reading
        if line.startswith("*"):
            continue

    raise Exception(f"IDLE termination failed: timeout waiting for {tag_str}")

def ping_server(mail, timeout=PING_TIMEOUT):
    """
    Send NOOP command to check if server is responsive.
    Returns True if server responds, False if timeout or error.
    """
    try:
        logger.debug("Sending NOOP ping to check server health...")
        tag = mail._new_tag()
        start_time = time.time()
        
        # Send NOOP command
        mail.send(f"{tag.decode()} NOOP\r\n".encode())
        
        # Wait for response with timeout
        while time.time() - start_time < timeout:
            try:
                response = mail.readline().decode().strip()
                if response.startswith(f"{tag.decode()} OK"):
                    logger.debug("Server ping successful")
                    return True
                elif response.startswith(f"{tag.decode()} NO") or response.startswith(f"{tag.decode()} BAD"):
                    logger.warning(f"Server ping failed: {response}")
                    return False
                # Ignore untagged responses and continue waiting
            except Exception as e:
                logger.warning(f"Error during ping: {e}")
                return False
                
        logger.warning(f"Server ping timeout after {timeout} seconds")
        return False
        
    except Exception as e:
        logger.error(f"Ping failed with exception: {e}")
        return False

def monitor_emails_for_account(email_account, password, imap_server, imap_port, company_id: str = None):
    """
    Monitor a single email account for new emails.
    """
    retry_count = 0
    max_retries = 5
    base_delay = 10  # Base delay in seconds
    
    try:
        # Connect to the server with timeout
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        # Set socket timeout to prevent hanging connections
        mail.sock.settimeout(300)  # 5 minutes timeout
        logger.info(f"Connected to IMAP server {imap_server}:{imap_port} for account: {email_account}")

        # Login to your email account
        mail.login(email_account, password)
        logger.info(f"Logged in as {email_account}")

        # Select the inbox
        mail.select("inbox")
        logger.info("Selected INBOX")

        # Get the current number of emails to skip existing ones
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        last_email_id = int(email_ids[-1]) if email_ids else 0
        logger.info(f"Last email ID before monitoring: {last_email_id}")

        # Start monitoring for new emails
        logger.info(f"Monitoring emails for account: {email_account}")
        logger.info(f"IDLE timeout: {IDLE_TIMEOUT}s ({IDLE_TIMEOUT//60}min), Ping timeout: {PING_TIMEOUT}s")
        while True:
            try:
                # Start IDLE mode
                # Start IDLE mode
                tag = mail._new_tag()
                mail.send(f"{tag.decode()} IDLE\r\n".encode())
                response = mail.readline().decode().strip()

                # Normal case: server sends "+ idling"
                if response.startswith("+"):
                    logger.debug("Entered IDLE mode")

                # Sometimes server replies with tagged OK immediately (means IDLE ended fast)
                elif response.startswith(tag.decode()):
                    logger.warning(f"IDLE ended immediately: {response}")
                    continue  # skip this iteration and restart loop

                # Any other response is unexpected
                else:
                    raise Exception(f"Unexpected IDLE response: {response}")


                # Wait for server notifications with timeout
                new_email_detected = False
                idle_start_time = time.time()
                
                while True:
                    # Check if we've exceeded the IDLE timeout
                    if time.time() - idle_start_time >= IDLE_TIMEOUT:
                        logger.info(f"IDLE timeout reached ({IDLE_TIMEOUT}s), performing health check...")
                        break
                    
                    # Set a short timeout for readline to avoid blocking indefinitely
                    try:
                        # Use select to check if data is available before reading
                        ready, _, _ = select.select([mail.sock], [], [], 1.0)  # 1 second timeout
                        
                        if ready:
                            line = mail.readline().decode().strip()
                            if line.startswith("*") and "EXISTS" in line:
                                new_email_detected = True
                                break
                            elif line.startswith("* BYE") or "TIMEOUT" in line:
                                raise Exception("Server disconnected or idle timeout")
                    except select.error:
                        # Fallback to regular readline if select fails
                        try:
                            line = mail.readline().decode().strip()
                            if line.startswith("*") and "EXISTS" in line:
                                new_email_detected = True
                                break
                            elif line.startswith("* BYE") or "TIMEOUT" in line:
                                raise Exception("Server disconnected or idle timeout")
                        except Exception:
                            time.sleep(0.1)  # Brief pause if reading fails

                # Terminate IDLE mode
                idle_done(mail, tag)
                
                if new_email_detected:
                    logger.info("New email detected, processing...")

                    # Search for all emails and process only those after the last known ID
                    status, messages = mail.search(None, "ALL")
                    email_ids = messages[0].split()
                    new_email_ids = [int(eid) for eid in email_ids if int(eid) > last_email_id]

                    if new_email_ids:
                        logger.info(f"Found {len(new_email_ids)} new emails")
                        for email_id in new_email_ids:
                            status, msg_data = mail.fetch(str(email_id), "(RFC822)")
                            for response_part in msg_data:
                                if isinstance(response_part, tuple):
                                    msg = email.message_from_bytes(response_part[1])
                                    logger.info(f"\nProcessing new email ID: {email_id}")
                                    process_email(msg, company_id=company_id)
                            last_email_id = email_id  # Update the last processed email ID

                    # Restart IDLE mode
                    logger.info("Re-entering IDLE mode...")
                else:
                    # IDLE timeout reached - perform health check
                    logger.info("IDLE timeout reached, performing server health check...")
                    
                    if ping_server(mail):
                        logger.info("Server health check passed, restarting IDLE...")
                    else:
                        logger.warning("Server health check failed, reconnecting...")
                        raise ConnectionResetError("Server ping failed - forcing reconnection")
            except (imaplib.IMAP4.abort, ConnectionResetError, ssl.SSLError, OSError, BrokenPipeError) as e:
                logger.error(f"Connection error detected: {e}. Attempting to reconnect...")
                retry_count += 1
                
                # Calculate exponential backoff delay
                delay = min(base_delay * (2 ** retry_count), 300)  # Cap at 5 minutes
                
                if retry_count >= max_retries:
                    logger.error(f"Max retries ({max_retries}) reached for account {email_account}. Waiting {delay} seconds before reset...")
                    retry_count = 0  # Reset retry count
                
                logger.info(f"Waiting {delay} seconds before reconnection attempt...")
                time.sleep(delay)
                
                try:
                    # Clean up existing connection
                    try:
                        mail.logout()
                    except:
                        pass  # Ignore logout errors for broken connections
                    
                    # Establish new connection
                    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                    # Set socket timeout to prevent hanging connections
                    mail.sock.settimeout(300)  # 5 minutes timeout
                    mail.login(email_account, password)
                    mail.select("inbox")
                    logger.info("Successfully reconnected and re-entering IDLE mode...")
                    
                    # Reset retry count on successful reconnection
                    retry_count = 0
                    
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error}")
                    continue  # Continue to retry
                    
            except Exception as e:
                logger.error(f"Unexpected error in IDLE loop: {e}")
                # For unexpected errors, also try to reconnect after a delay
                time.sleep(30)
                try:
                    mail.logout()
                except:
                    pass
                try:
                    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                    # Set socket timeout to prevent hanging connections
                    mail.sock.settimeout(300)  # 5 minutes timeout
                    mail.login(email_account, password)
                    mail.select("inbox")
                    logger.info("Reconnected after unexpected error...")
                except Exception as reconnect_error:
                    logger.error(f"Reconnection after unexpected error failed: {reconnect_error}")
                    continue

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        try:
            mail.logout()
            logger.info("Logged out from IMAP server")
        except:
            pass

def monitor_new_emails():
    """
    Monitor multiple email accounts for new emails.
    """
    # Ensure tables exist
    try:
        create_tables_if_not_exist()
    except Exception as e:
        logger.warning(f"Table creation check failed: {e}")

    email_accounts = get_email_accounts()
    
    if not email_accounts:
        logger.error("No email accounts found in environment variables.")
        logger.error("Please set EMAIL_ACCOUNT_1 and EMAIL_PASSWORD_1 (or legacy EMAIL_ACCOUNT and EMAIL_PASSWORD) in your .env file.")
        return
    
    logger.info(f"Found {len(email_accounts)} email accounts to monitor")
    logger.info("Starting to monitor new emails")
    
    # Start monitoring each account in a separate thread
    threads = []
    
    for account in email_accounts:
        thread = threading.Thread(
            target=monitor_emails_for_account,
            args=(account["account"], account["password"], account["imap_server"], account["imap_port"], account.get("company_id")),
            daemon=True
        )
        threads.append(thread)
        thread.start()
        logger.info(f"Started monitoring for account: {account['account']}")
    
    # Wait for all threads to complete (they won't, as they run indefinitely)
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    monitor_new_emails()