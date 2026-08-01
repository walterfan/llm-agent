"""Email API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.email_log import EmailLog, SEND_TYPE_MANUAL
from app.models.user import User
from app.schemas.email import (
    EmailDeliveryResult,
    EmailLogListResponse,
    EmailLogResponse,
    EmailPreferencesResponse,
    EmailPreferencesUpdate,
    EmailSendRequest,
    EmailSendResponse,
)
from app.services.email_service import EmailService
from app.services.email_template_service import EmailTemplateService
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_email_background_task(
    user_id: int,
    user_full_name: str | None,
    city: str,
    recipient_emails: list[str],
    days: int,
):
    """
    Background task to generate recommendations and send emails.

    This runs asynchronously after the API returns, preventing timeout issues.
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        logger.info(
            f"📧 Background task started: user_id={user_id}, city={city}, days={days}, recipients={len(recipient_emails)}"
        )

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"❌ Background task: User {user_id} not found")
            return

        # Generate recommendations
        recommendation_service = RecommendationService(db)
        try:
            logger.info(f"🔄 Generating {days}-day recommendations for user {user_id}")
            multi_day_recommendation = await recommendation_service.generate_multi_day(
                user=user,
                city=city,
                days=days,
            )
            logger.info(
                f"✅ Generated {len(multi_day_recommendation.recommendations)} recommendations"
            )
        except Exception as e:
            logger.error(f"❌ Failed to generate recommendations: {e}", exc_info=True)
            # Log failed attempt
            for recipient in recipient_emails:
                email_log = EmailLog(
                    user_id=user_id,
                    recommendation_id=None,
                    recipient_email=recipient,
                    status="failed",
                    send_type=SEND_TYPE_MANUAL,
                    error_message=f"Failed to generate recommendations: {str(e)}",
                )
                db.add(email_log)
            db.commit()
            return

        # Render email template
        template_service = EmailTemplateService()
        logger.info(f"📝 Rendering email template for {multi_day_recommendation.city}")
        html_body, text_body = template_service.render_multi_day_recommendation_email(
            user_name=user_full_name or "用户",
            city=multi_day_recommendation.city,
            recommendations=multi_day_recommendation.recommendations,
            unsubscribe_url=f"#unsubscribe-{user_id}",
        )

        # Get first recommendation ID for logging
        first_rec_id = (
            multi_day_recommendation.recommendations[0].recommendation.id
            if multi_day_recommendation.recommendations
            else None
        )

        # Send emails
        email_service = EmailService()
        logger.info(
            f"📤 Sending emails to {len(recipient_emails)} recipient(s): {', '.join(recipient_emails)}"
        )
        results = await email_service.send_email(
            to_emails=recipient_emails,
            subject=f"未来{days}天穿衣推荐 - {multi_day_recommendation.city}",
            html_body=html_body,
            text_body=text_body,
        )

        # Log email deliveries
        for recipient, status in results.items():
            error_message = None
            if status == "failed":
                error_message = "SMTP send failed"
                logger.error(f"❌ Email failed: {recipient}")
            else:
                logger.info(f"✅ Email sent: {recipient}")

            email_log = EmailLog(
                user_id=user_id,
                recommendation_id=first_rec_id,
                recipient_email=recipient,
                status=status,
                send_type=SEND_TYPE_MANUAL,
                error_message=error_message,
            )
            db.add(email_log)

        db.commit()

        success_count = sum(1 for status in results.values() if status == "sent")
        failed_count = len(results) - success_count
        logger.info(
            f"📊 Background task completed: {success_count} sent, {failed_count} failed "
            f"(total: {len(recipient_emails)})"
        )

    except Exception as e:
        logger.error(f"❌ Background task unexpected error: {e}", exc_info=True)
    finally:
        db.close()


@router.get("/users/me/email-preferences", response_model=EmailPreferencesResponse)
def get_email_preferences(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailPreferencesResponse:
    """
    Get current user's email notification preferences.

    Requires authentication.
    """
    from app.services.user_service import UserService

    preferences = UserService.get_email_preferences(db, current_user)
    return EmailPreferencesResponse(**preferences)


@router.patch("/users/me/email-preferences", response_model=EmailPreferencesResponse)
def update_email_preferences(
    preferences_update: EmailPreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailPreferencesResponse:
    """
    Update current user's email notification preferences.

    Requires authentication.
    """
    from app.services.user_service import UserService

    updated_user = UserService.update_email_preferences(
        db, current_user, preferences_update
    )
    preferences = UserService.get_email_preferences(db, updated_user)
    return EmailPreferencesResponse(**preferences)


@router.post("/recommendations/send-email", response_model=EmailSendResponse)
async def send_recommendation_email(
    request: EmailSendRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailSendResponse:
    """
    Manually send recommendation email to specified recipients.

    This endpoint returns immediately and processes email sending in the background
    to avoid timeout issues. Check email logs to verify delivery status.

    Requires authentication. Manual email sends are always allowed regardless of
    email_notifications_enabled setting (which only controls scheduled daily emails).
    """

    # Validate request
    if not request.recipient_emails:
        logger.warning(
            f"User {current_user.id} attempted to send email with no recipients"
        )
        raise HTTPException(
            status_code=400, detail="At least one recipient email is required"
        )

    # Get days from request, default to 3
    days = getattr(request, "days", 3) or 3
    days = max(1, min(days, 3))  # Clamp to 1-3

    logger.info(
        f"📧 Email request received: user_id={current_user.id}, user_email={current_user.email}, "
        f"city={request.city}, days={days}, recipients={len(request.recipient_emails)}"
    )
    logger.info(f"   Recipients: {', '.join(request.recipient_emails)}")

    # Add background task
    background_tasks.add_task(
        _send_email_background_task,
        user_id=current_user.id,
        user_full_name=current_user.full_name,
        city=request.city,
        recipient_emails=request.recipient_emails,
        days=days,
    )

    # Return immediately with pending status
    deliveries = [
        EmailDeliveryResult(
            recipient_email=email,
            status="pending",
            error_message=None,
        )
        for email in request.recipient_emails
    ]

    logger.info(
        f"✅ Email request accepted: {len(request.recipient_emails)} recipient(s) queued for background processing"
    )

    return EmailSendResponse(
        success=True,
        message=f"Email sending initiated for {len(request.recipient_emails)} recipient(s). Processing in background. Check email logs for delivery status.",
        deliveries=deliveries,
    )


@router.get("/users/me/email-logs", response_model=EmailLogListResponse)
def get_email_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> EmailLogListResponse:
    """
    Get current user's email delivery history.

    Requires authentication.
    """
    query = db.query(EmailLog).filter(EmailLog.user_id == current_user.id)
    total = query.count()
    logs = query.order_by(EmailLog.sent_at.desc()).offset(offset).limit(limit).all()

    return EmailLogListResponse(
        total=total,
        items=[EmailLogResponse.model_validate(log) for log in logs],
    )
