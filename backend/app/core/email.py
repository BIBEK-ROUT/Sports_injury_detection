import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def send_smtp_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Sends an email using standard SMTP.
    Works perfectly with Gmail App Passwords.
    """
    # If not configured, log and return false
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(
            "SMTP email credentials are not configured in .env. "
            "Email cannot be sent. Printing email content to logs:\n"
            f"TO: {to_email}\nSUBJECT: {subject}\nCONTENT: {html_content[:300]}..."
        )
        return False

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM or settings.SMTP_USERNAME}>"
        msg["To"] = to_email

        # Attach text part
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        else:
            msg.attach(MIMEText("Please enable HTML to view this message.", "plain", "utf-8"))

        # Attach HTML part
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Connect to SMTP server
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.ehlo()
        
        # Start TLS for security
        if settings.SMTP_PORT == 587:
            server.starttls()
            server.ehlo()

        # Login and send
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USERNAME, to_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email successfully sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
        return False


def get_reset_email_template(reset_url: str, first_name: str) -> str:
    """HTML template for password reset email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reset Your SportGuard Password</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f3f4f6;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                overflow: hidden;
                border: 1px solid #e5e7eb;
            }}
            .header {{
                background-color: #1e3a8a;
                color: #ffffff;
                padding: 24px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
            }}
            .content {{
                padding: 32px 24px;
                color: #374151;
                line-height: 1.6;
            }}
            .btn-container {{
                text-align: center;
                margin: 32px 0;
            }}
            .btn {{
                background-color: #2563eb;
                color: #ffffff !important;
                padding: 12px 28px;
                text-decoration: none;
                font-weight: 600;
                border-radius: 6px;
                display: inline-block;
                box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 16px 24px;
                text-align: center;
                font-size: 12px;
                color: #6b7280;
                border-top: 1px solid #e5e7eb;
            }}
            .note {{
                font-size: 12px;
                color: #9ca3af;
                margin-top: 24px;
                border-top: 1px dashed #e5e7eb;
                padding-top: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>SportGuard</h1>
            </div>
            <div class="content">
                <p>Hello {first_name},</p>
                <p>We received a request to reset the password for your SportGuard account. Click the button below to set a new password:</p>
                <div class="btn-container">
                    <a href="{reset_url}" class="btn">Reset Password</a>
                </div>
                <p>This link will expire in 15 minutes. If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                <p class="note">If you're having trouble clicking the button, copy and paste the URL below into your web browser:<br>
                <a href="{reset_url}">{reset_url}</a></p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year if 'datetime' in globals() else 2026} SportGuard. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
