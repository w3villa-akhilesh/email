# error_notifier/email_notifier.py
import os
import traceback
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

EXCEPTION_NOTIFIER_API_KEY = os.getenv("EXCEPTION_NOTIFIER_API_KEY")
EXCEPTION_NOTIFIER_SENDER = os.getenv("EXCEPTION_NOTIFIER_SENDER")
EXCEPTION_NOTIFIER_RECIPIENT = os.getenv("EXCEPTION_NOTIFIER_RECIPIENTS", "").split(",")

def send_exception_email(error: Exception, context: str = "No context provided", session_id=None, origin=None, company_id=None):
    """Send error email using SendGrid."""
    if not EXCEPTION_NOTIFIER_API_KEY:
        print("SendGrid API key not set.")
        return

    subject_parts = [f"Error: {type(error).__name__}"]
    if session_id:
        subject_parts.append(f"Session ID- {session_id}")
    if company_id:
        subject_parts.append(f"Company ID- {company_id}")
    if origin:
        subject_parts.append(f"Origin- {origin}")

    subject = " | ".join(subject_parts)
    error_trace = traceback.format_exc()
    body = f"""
    <strong>KIVO AGENT ERROR Context:</strong><br>
    {context}<br><br>
    <strong>Error Type:</strong> {type(error).__name__}<br>
    <strong>Error Message:</strong> {str(error)}<br><br>
    <strong>Traceback:</strong><br>
    <pre>{error_trace}</pre>
    """

    message = Mail(
        from_email=EXCEPTION_NOTIFIER_SENDER,
        to_emails=EXCEPTION_NOTIFIER_RECIPIENT,
        subject=subject,
        html_content=body
    )
    print(f"Subject-----> {subject}")
    print( f"Sending error email------> {error}" )

    try:
        sg = SendGridAPIClient(EXCEPTION_NOTIFIER_API_KEY)
        response = sg.send(message)
        print(f"Error email sent: {response.status_code}")
    except Exception as send_error:
        print(f"Failed to send error email: {send_error}")
