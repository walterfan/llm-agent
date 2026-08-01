"""Admin endpoints for managing recommendations on behalf of users."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.recommendation import (
    AdminGenerateMultiDayRequest,
    DailyRecommendation,
    MultiDayRecommendationResponse,
    RecommendationResponse,
    UserBasicInfo,
)
from app.services.email_service import EmailService
from app.services.recommendation_service import RecommendationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-for-user", response_model=MultiDayRecommendationResponse)
async def generate_multi_day_recommendation_for_user(
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_permission("recommendation.admin"))],
    request: AdminGenerateMultiDayRequest,
) -> MultiDayRecommendationResponse:
    """
    Generate 3-day AI Recommendations for a specific user (admin only).

    This endpoint allows administrators to:
    - Select any user in the system
    - Generate recommendations for today, tomorrow, and the day after tomorrow
    - Optionally send the recommendations via email

    **Permission Required**: `recommendation.admin`

    **Rate Limit**: 10 requests/hour per admin (TODO: implement rate limiting)

    Args:
        request: AdminGenerateMultiDayRequest with user_id, city_code, send_email

    Returns:
        MultiDayRecommendationResponse with 3 daily recommendations

    Raises:
        404: User not found
        400: User profile incomplete or city invalid
        500: LLM generation or email sending failed
    """
    logger.info(
        f"Admin {admin_user.email} (id={admin_user.id}) generating 3-day recommendations "
        f"for user_id={request.user_id}, city_code={request.city_code}"
    )

    # Get target user
    target_user = UserService.get_user_by_id(db, request.user_id)
    if not target_user:
        logger.warning(f"User not found: user_id={request.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {request.user_id} not found",
        )

    # Check if target user has complete profile
    if not target_user.gender or not target_user.age:
        logger.warning(f"User {target_user.id} has incomplete profile")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile is incomplete. Gender and age are required for recommendations.",
        )

    # Generate 3-day recommendations
    rec_service = RecommendationService(db)
    try:
        recommendations = await rec_service.generate_for_user_multi_day(
            target_user=target_user, city_code=request.city_code, days=3
        )
    except ValueError as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error generating recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations. Please try again later.",
        )

    # Build daily recommendation responses
    daily_recommendations = []
    for rec in recommendations:
        # Parse weather data to create summary
        weather_data = rec.weather_data
        weather_summary = (
            f"{weather_data.get('weather_text', 'N/A')}, "
            f"最高{weather_data.get('temperature_high', 'N/A')}°C, "
            f"最低{weather_data.get('temperature_low', 'N/A')}°C"
        )

        # Build RecommendationResponse from Recommendation model
        rec_response = RecommendationResponse(
            id=rec.id,
            user_id=rec.user_id,
            city=rec.city,
            weather_data=rec.weather_data,
            clothing_items=rec.response.get("clothing_items", []),
            advice=rec.response.get("advice", ""),
            weather_warnings=rec.response.get("weather_warnings"),
            emoji_summary=rec.response.get("emoji_summary", ""),
            cached=False,
            cost_estimate=rec.cost_estimate,
            created_at=rec.created_at,
        )

        daily_rec = DailyRecommendation(
            date=weather_data.get(
                "date", rec.forecast_date.isoformat() if rec.forecast_date else ""
            ),
            date_label=weather_data.get("date_label", ""),
            recommendation=rec_response,
            weather_summary=weather_summary,
        )
        daily_recommendations.append(daily_rec)

    # Send email if requested
    email_sent = False
    if request.send_email:
        logger.info(f"Sending multi-day email to {target_user.email}")
        try:
            email_service = EmailService()
            await email_service.send_multi_day_recommendation(
                user=target_user,
                recommendations=recommendations,
                city=recommendations[0].city if recommendations else "Unknown",
            )
            email_sent = True
            logger.info(f"✅ Email sent successfully to {target_user.email}")
        except Exception as e:
            logger.error(
                f"Failed to send email to {target_user.email}: {e}", exc_info=True
            )
            # Don't fail the entire request if email fails
            logger.warning("Continuing without email notification")

    # Build response
    response = MultiDayRecommendationResponse(
        user=UserBasicInfo(
            id=target_user.id,
            email=target_user.email,
            full_name=target_user.full_name,
        ),
        city=recommendations[0].city if recommendations else "Unknown",
        city_code=request.city_code,
        recommendations=daily_recommendations,
        email_sent=email_sent,
        generated_at=datetime.utcnow(),
    )

    logger.info(
        f"✅ Successfully generated 3-day recommendations for user {target_user.id}. "
        f"Email sent: {email_sent}"
    )

    return response
