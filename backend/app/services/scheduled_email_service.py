"""
Scheduled Email Service

This service handles scheduling and sending of daily dress recommendation emails.
It coordinates with the recommendation service, weather service, and email service
to generate and send scheduled emails to users based on their preferences.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.email_log import EmailLog, SEND_TYPE_SCHEDULED
from app.models.user import User
from app.services.email_service import EmailService
from app.services.email_template_service import EmailTemplateService
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class ScheduledEmailService:
    """Service for handling scheduled email recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self.recommendation_service = RecommendationService(db)
        self.email_service = EmailService()
        self.template_service = EmailTemplateService()

    def get_users_for_hour(self, hour: int) -> list[User]:
        """
        Get all users who should receive emails at the specified hour.

        Args:
            hour: Hour in 24-hour format (0-23) in Asia/Shanghai timezone

        Returns:
            List of User objects with email notifications enabled for this hour
        """
        # Format hour as HH:00 (e.g., "08:00", "14:00")
        time_str = f"{hour:02d}:00"

        logger.info(f"🔍 Querying users with email_send_time={time_str}")

        users = (
            self.db.query(User)
            .filter(
                User.email_notifications_enabled == True,  # noqa: E712
                User.email_send_time == time_str,
                User.is_active == True,  # noqa: E712
            )
            .all()
        )

        logger.info(f"📊 Found {len(users)} user(s) scheduled for {time_str}")
        return users

    async def send_scheduled_email(self, user_id: int) -> dict[str, any]:
        """
        Send scheduled email recommendation to a user.

        This method:
        1. Fetches user and validates email preferences
        2. Generates 3-day recommendations for user's preferred city
        3. Renders email template
        4. Sends emails to user + additional recipients
        5. Logs all email deliveries

        Args:
            user_id: ID of the user to send email to

        Returns:
            Dictionary with status and details:
            {
                "status": "success" | "error",
                "user_id": int,
                "emails_sent": int,
                "emails_failed": int,
                "error": str (if error)
            }
        """
        logger.info(f"📧 Starting scheduled email for user_id={user_id}")

        try:
            # 1. Get user from database
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                error_msg = f"User {user_id} not found"
                logger.error(f"❌ {error_msg}")
                return {"status": "error", "user_id": user_id, "error": error_msg}

            # Validate email preferences
            if not user.email_notifications_enabled:
                error_msg = f"User {user_id} has email notifications disabled"
                logger.warning(f"⚠️  {error_msg}")
                return {"status": "error", "user_id": user_id, "error": error_msg}

            if not user.preferred_city:
                error_msg = f"User {user_id} has no preferred_city set"
                logger.error(f"❌ {error_msg}")
                return {"status": "error", "user_id": user_id, "error": error_msg}

            # Build recipient list (user + additional recipients)
            recipients = [user.email]
            if user.additional_email_recipients:
                additional = [
                    email.strip()
                    for email in user.additional_email_recipients.split(",")
                    if email.strip()
                ]
                recipients.extend(additional)

            logger.info(f"📬 Recipients for user {user_id}: {len(recipients)} email(s)")

            # 2. Generate 3-day recommendations
            logger.info(
                f"🔄 Generating 3-day recommendations for city {user.preferred_city}"
            )
            try:
                multi_day_recommendation = (
                    await self.recommendation_service.generate_multi_day(
                        user=user,
                        city=user.preferred_city,
                        days=3,
                    )
                )
                logger.info(
                    f"✅ Generated {len(multi_day_recommendation.recommendations)} recommendations"
                )
            except Exception as e:
                error_msg = f"Failed to generate recommendations: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                # Log failed attempt for all recipients
                for recipient in recipients:
                    email_log = EmailLog(
                        user_id=user_id,
                        recommendation_id=None,
                        recipient_email=recipient,
                        status="failed",
                        send_type=SEND_TYPE_SCHEDULED,
                        error_message=error_msg,
                    )
                    self.db.add(email_log)
                self.db.commit()
                return {
                    "status": "error",
                    "user_id": user_id,
                    "error": error_msg,
                    "emails_sent": 0,
                    "emails_failed": len(recipients),
                }

            # 3. Render email template
            logger.info(
                f"📝 Rendering email template for {multi_day_recommendation.city}"
            )
            html_body, text_body = (
                self.template_service.render_multi_day_recommendation_email(
                    user_name=user.full_name or "用户",
                    city=multi_day_recommendation.city,
                    recommendations=multi_day_recommendation.recommendations,
                    unsubscribe_url=f"#unsubscribe-{user_id}",  # TODO: Implement unsubscribe
                )
            )

            # Get first recommendation ID for logging
            first_rec_id = (
                multi_day_recommendation.recommendations[0].recommendation.id
                if multi_day_recommendation.recommendations
                else None
            )

            # 4. Send emails
            logger.info(
                f"📤 Sending scheduled emails to {len(recipients)} recipient(s)"
            )
            results = await self.email_service.send_email(
                to_emails=recipients,
                subject=f"每日穿衣推荐 - {multi_day_recommendation.city}",
                html_body=html_body,
                text_body=text_body,
            )

            # 5. Log email deliveries
            success_count = 0
            failed_count = 0

            for recipient, status in results.items():
                error_message = None
                if status == "failed":
                    error_message = "SMTP send failed"
                    logger.error(f"❌ Scheduled email failed: {recipient}")
                    failed_count += 1
                else:
                    logger.info(f"✅ Scheduled email sent: {recipient}")
                    success_count += 1

                email_log = EmailLog(
                    user_id=user_id,
                    recommendation_id=first_rec_id,
                    recipient_email=recipient,
                    status=status,
                    send_type=SEND_TYPE_SCHEDULED,
                    error_message=error_message,
                )
                self.db.add(email_log)

            self.db.commit()

            logger.info(
                f"📊 Scheduled email completed for user {user_id}: "
                f"{success_count} sent, {failed_count} failed"
            )

            return {
                "status": "success",
                "user_id": user_id,
                "emails_sent": success_count,
                "emails_failed": failed_count,
                "total_recipients": len(recipients),
            }

        except Exception as e:
            logger.error(
                f"❌ Unexpected error sending scheduled email for user {user_id}: {e}",
                exc_info=True,
            )
            self.db.rollback()
            return {
                "status": "error",
                "user_id": user_id,
                "error": str(e),
                "emails_sent": 0,
                "emails_failed": 0,
            }

    async def send_emails_for_hour(self, hour: int) -> dict[str, int]:
        """
        Send scheduled emails to all users who should receive emails at this hour.

        This is called by the cronjob endpoint every hour. It queries users and sends
        emails directly (no Celery, no queueing).

        Args:
            hour: Hour in 24-hour format (0-23) in Asia/Shanghai timezone

        Returns:
            Dictionary with counts:
            {
                "processed_count": 10,
                "success_count": 8,
                "failed_count": 2
            }
        """
        logger.info(f"⏰ Processing scheduled emails for hour {hour:02d}:00")

        users = self.get_users_for_hour(hour)

        if not users:
            logger.info(f"📭 No users scheduled for hour {hour:02d}:00")
            return {
                "processed_count": 0,
                "success_count": 0,
                "failed_count": 0,
            }

        processed_count = 0
        success_count = 0
        failed_count = 0

        for user in users:
            try:
                logger.info(
                    f"📧 Sending scheduled email for user {user.id} ({user.email})"
                )
                result = await self.send_scheduled_email(user.id)

                processed_count += 1
                if result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(
                    f"❌ Failed to send scheduled email for user {user.id}: {e}",
                    exc_info=True,
                )
                processed_count += 1
                failed_count += 1

        logger.info(
            f"📊 Completed scheduled emails for hour {hour:02d}:00: "
            f"{success_count} success, {failed_count} failed, {processed_count} total"
        )

        return {
            "processed_count": processed_count,
            "success_count": success_count,
            "failed_count": failed_count,
        }
