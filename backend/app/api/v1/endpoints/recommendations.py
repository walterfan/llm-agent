"""Recommendations API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user_from_query, get_db
from app.models.user import User
from app.schemas.recommendation import (
    MultiDayRecommendationResponse,
    RecommendationCreate,
    RecommendationListResponse,
    RecommendationResponse,
)
from app.services.recommendation_service import RecommendationService
from app.services.streaming_recommendation_service import StreamingRecommendationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=MultiDayRecommendationResponse, status_code=200)
async def generate_recommendation(
    request: RecommendationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Generate personalized 1-3 day AI Recommendations.

    Requires authentication. Fetches weather forecast for the specified city,
    analyzes user profile, and generates AI-powered clothing suggestions for 3 days.

    Recommendations are saved to the database for history tracking.
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.generate_multi_day(
            user=current_user,
            city=request.city,
            days=request.days,
        )
        logger.info(
            f"📤 Returning {len(recommendations.recommendations)} day(s) of recommendations to client"
        )
        return recommendations
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="抱歉，推荐服务暂时不可用，请稍后再试。"
        )


@router.get("/", response_model=RecommendationListResponse)
async def list_recommendations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    start_date: str | None = Query(
        None, description="Filter by start date (ISO format)"
    ),
    end_date: str | None = Query(None, description="Filter by end date (ISO format)"),
):
    """
    List user's recommendation history (past 14 days).

    Requires authentication. Returns paginated list of recommendations
    ordered by creation date (newest first).
    """
    try:
        service = RecommendationService(db)
        recommendations, total = service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )

        # Convert to response format
        items = []
        for rec in recommendations:
            response_data = rec.response
            items.append(
                RecommendationResponse(
                    id=rec.id,
                    user_id=rec.user_id,
                    city=rec.city,
                    weather_data=rec.weather_data,
                    clothing_items=response_data.get("clothing_items", []),
                    advice=response_data.get("advice", ""),
                    weather_warnings=response_data.get("weather_warnings"),
                    emoji_summary=response_data.get("emoji_summary", ""),
                    cached=False,
                    cost_estimate=rec.cost_estimate,
                    created_at=rec.created_at,
                )
            )

        return RecommendationListResponse(
            items=items, total=total, limit=limit, offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to list recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recommendations"
        )


@router.get("/stream", response_class=StreamingResponse)
async def generate_recommendation_stream(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_from_query)],
    city: str = Query(..., description="City name or AD code"),
    date: str | None = Query(None, description="Date for recommendation (ISO format)"),
):
    """
    Generate a streaming dress recommendation using Server-Sent Events (SSE).

    This endpoint streams the recommendation generation process in real-time,
    allowing the frontend to display progressive updates as the AI generates
    the response.

    **Note**: Uses GET method because EventSource only supports GET requests.

    **Authentication**: Due to EventSource limitations, pass token as query parameter:
    `/stream?city=340100&token=your_jwt_token`

    **Response Format**: Server-Sent Events (text/event-stream)

    **Event Types**:
    - `start`: Initialization message
    - `token`: Individual LLM tokens as they arrive
    - `data`: Structured data chunks (weather, status updates)
    - `error`: Error occurred during generation
    - `done`: Generation complete

    **Example Events**:
    ```
    data: {"type":"start","message":"正在生成推荐..."}

    data: {"type":"data","field":"weather","value":{"city":"合肥","temperature":6}}

    data: {"type":"token","content":"建议"}

    data: {"type":"token","content":"穿"}

    data: {"type":"done","message":"推荐生成完成！","recommendation_id":"uuid"}
    ```

    **Frontend Usage** (JavaScript):
    ```javascript
    const eventSource = new EventSource('/api/v1/recommendations/stream?city=340100&token=YOUR_TOKEN');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'token') {
            // Append token to UI
            displayToken(data.content);
        } else if (data.type === 'done') {
            // Close stream
            eventSource.close();
        }
    };
    ```
    """
    logger.info(
        f"🌊 [STREAM] Request received: method={request.method}, url={request.url}, user={current_user.email}"
    )
    logger.debug(
        f"🌊 [STREAM] Query params: city={city}, date={date}, has_token={'token' in request.url.query}"
    )
    try:
        service = StreamingRecommendationService(db)

        return StreamingResponse(
            service.generate_recommendation_stream(
                user=current_user, city=city, date=date
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except Exception as e:
        logger.error(f"Failed to start streaming recommendation: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start streaming recommendation"
        )


@router.get("/stream/3days", response_class=StreamingResponse)
async def generate_recommendation_stream_3days(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_from_query)],
    city: str = Query(..., description="City name or AD code"),
    days: int = Query(3, ge=1, le=3, description="Number of days to stream (1-3)"),
):
    """
    Generate a 3-day streaming dress recommendation using Server-Sent Events (SSE).

    Keeps `/stream` single-day. This endpoint streams three days sequentially:
    today, tomorrow, and the day after tomorrow.

    **Authentication**: pass token as query parameter:
    `/stream/3days?city=430100&token=your_jwt_token`
    """
    logger.info(
        f"🌊 [STREAM-3D] Request received: method={request.method}, url={request.url}, user={current_user.email}"
    )
    try:
        service = StreamingRecommendationService(db)
        return StreamingResponse(
            service.generate_recommendation_stream_3days(
                user=current_user,
                city=city,
                days=days,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Failed to start 3-day streaming recommendation: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start 3-day streaming recommendation"
        )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Get a specific recommendation by ID.

    Requires authentication. User can only access their own recommendations.
    """
    try:
        service = RecommendationService(db)
        recommendation = service.get_recommendation_by_id(
            recommendation_id, current_user.id
        )

        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        response_data = recommendation.response
        return RecommendationResponse(
            id=recommendation.id,
            user_id=recommendation.user_id,
            city=recommendation.city,
            weather_data=recommendation.weather_data,
            clothing_items=response_data.get("clothing_items", []),
            advice=response_data.get("advice", ""),
            weather_warnings=response_data.get("weather_warnings"),
            emoji_summary=response_data.get("emoji_summary", ""),
            cached=False,
            cost_estimate=recommendation.cost_estimate,
            created_at=recommendation.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recommendation")
