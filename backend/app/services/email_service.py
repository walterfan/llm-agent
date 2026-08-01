"""Email service for sending SMTP emails."""

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import aiosmtplib

from app.core.config import settings
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.email_template_service import EmailTemplateService

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        """Initialize SMTP client with configuration from settings."""
        self.server = settings.MAIL_SERVER
        self.port = settings.MAIL_PORT
        self.use_ssl = settings.MAIL_USE_SSL
        self.use_tls = settings.MAIL_USE_TLS
        self.username = settings.MAIL_USERNAME
        self.password = settings.MAIL_PASSWORD
        self.sender = settings.MAIL_SENDER

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> dict[str, str]:
        """
        Send email to specified recipients.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, defaults to stripped HTML)

        Returns:
            Dictionary mapping recipient email to status ("sent" or "failed")
        """
        if not self.sender or not self.username or not self.password:
            logger.error("Email configuration incomplete. Cannot send emails.")
            return {email: "failed" for email in to_emails}

        results = {}
        for recipient in to_emails:
            try:
                # Create message
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = self.sender
                message["To"] = recipient

                # Add plain text part
                if text_body:
                    text_part = MIMEText(text_body, "plain", "utf-8")
                    message.attach(text_part)
                else:
                    # Generate plain text from HTML (simple strip)
                    import re

                    text_content = re.sub(r"<[^>]+>", "", html_body)
                    text_part = MIMEText(text_content, "plain", "utf-8")
                    message.attach(text_part)

                # Add HTML part
                html_part = MIMEText(html_body, "html", "utf-8")
                message.attach(html_part)

                # Send email
                await self._send_smtp(message, recipient)
                results[recipient] = "sent"
                logger.info(f"Email sent successfully to {recipient}")

            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}")
                results[recipient] = "failed"

        return results

    async def _send_smtp(
        self, message: MIMEMultipart, recipient: str, retries: int = 3
    ) -> None:
        """
        Send email via SMTP with retry logic.

        Args:
            message: MIME message to send
            recipient: Recipient email address (for logging)
            retries: Number of retry attempts

        Raises:
            Exception: If all retries fail
        """
        last_error = None
        for attempt in range(retries):
            smtp = None
            try:
                # Create SMTP connection with timeout
                # For SSL (port 465): use_tls should be False
                # For TLS/STARTTLS (port 587): use_tls should be True
                if self.use_ssl:
                    # SSL connection (port 465)
                    smtp = aiosmtplib.SMTP(
                        hostname=self.server,
                        port=self.port,
                        use_tls=False,  # SSL doesn't use STARTTLS
                        timeout=30.0,  # 30 second timeout
                    )
                else:
                    # TLS/STARTTLS connection (port 587)
                    smtp = aiosmtplib.SMTP(
                        hostname=self.server,
                        port=self.port,
                        use_tls=False,  # Will call starttls() explicitly
                        timeout=30.0,  # 30 second timeout
                    )

                logger.info(
                    f"Connecting to SMTP server {self.server}:{self.port} (SSL={self.use_ssl}, TLS={self.use_tls})"
                )
                await smtp.connect()

                # For non-SSL connections, use STARTTLS if configured
                if self.use_tls and not self.use_ssl:
                    logger.info("Upgrading connection with STARTTLS")
                    await smtp.starttls()

                logger.info(f"Logging in as {self.username}")
                await smtp.login(self.username, self.password)

                logger.info(f"Sending message to {recipient}")
                await smtp.send_message(message)

                await smtp.quit()
                logger.info(f"✅ Email sent successfully to {recipient}")

                return  # Success

            except Exception as e:
                last_error = e
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                logger.error(
                    f"SMTP send attempt {attempt + 1}/{retries} failed for {recipient}: {type(e).__name__}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                if attempt < retries - 1:
                    await asyncio.sleep(wait_time)

                # Ensure connection is closed
                if smtp:
                    try:
                        await smtp.quit()
                    except:
                        pass

        # All retries failed
        raise Exception(f"Failed to send email after {retries} attempts: {last_error}")

    async def send_multi_day_recommendation(
        self,
        user: User,
        recommendations: List[Recommendation],
        city: str,
    ) -> dict[str, str]:
        """
        Send multi-day dress recommendation email to user.

        Args:
            user: User to send email to
            recommendations: List of 3 Recommendation objects (today, tomorrow, day+2)
            city: City name

        Returns:
            Dictionary mapping recipient email to status ("sent" or "failed")
        """
        if not user.email:
            logger.warning(f"User {user.id} has no email address")
            return {user.email or "": "failed"}

        # Render multi-day email template
        template_service = EmailTemplateService()
        html_body, text_body = template_service.render_multi_day_recommendation_email(
            user_name=user.full_name or user.email,
            city=city,
            recommendations=recommendations,
        )

        # Send email
        subject = f"🌤️ 未来三天穿衣建议 - {city}"
        return await self.send_email(
            to_emails=[user.email],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
