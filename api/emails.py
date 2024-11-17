import resend
from pydantic import ValidationError
from flask import current_app
from models import EmailRequest, EmailWithAttachmentRequest
import logging

resend.api_key = current_app.config["RESEND_API_KEY"]
sender_email_account = current_app.config["SENDER_EMAIL_ACCOUNT"]

def send_email_to_user(email_request: EmailRequest) -> bool:
    try:
        email_request_validated = EmailRequest.model_validate(email_request)

        params: resend.Emails.SendParams = {
                "from": sender_email_account,
                "to": [email_request_validated.email_account],
                "subject": email_request_validated.subject,
                "text": email_request_validated.message
        }

        email_attempt = resend.Emails.send(params)
        if email_attempt["id"] is None:
            logging.error("Could not send email.")
            return False
        else:
            return True

    except ValidationError as e:
         logging.error("ValidationError: %s", e)
         return False

    except Exception as e:
         logging.error("Exception: %s", e)
         return False

def send_email_with_attachment(email_request: EmailWithAttachmentRequest) -> bool:
    try:
        email_request_validated = EmailWithAttachmentRequest.model_validate(email_request)

        params: resend.Emails.SendParams = {
            "from": sender_email_account,
            "to": [email_request_validated.email_account],
            "subject": email_request_validated.subject,
            "text": email_request_validated.message
        }

        if email_request_validated.attachment_content and email_request_validated.attachment_filename:
            params["attachments"] = [{
                "content": email_request_validated.attachment_content,
                "filename": email_request_validated.attachment_filename
            }]
        else:
            logging.info("No attachments with email.")

        email_attempt = resend.Emails.send(params)
        if email_attempt["id"] is None:
            logging.error("Error sending email.")
            return False
        logging.info("Successfully sent email with optional attachment!")
        return True
    except ValidationError as e:
         logging.error("ValidationError: %s", e)
         return False

    except Exception as e:
         logging.error("Exception: %s", e)
         return False



