"""Recommendation schemas."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationOutput(BaseModel):
    """Structured output from LLM for AI Recommendations."""

    clothing_items: list[str] = Field(
        ...,
        description="List of specific clothing items (e.g., ['羽绒服', '保暖裤', '围巾'])",
    )
    advice: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Personalized advice (3-5 sentences with emojis)",
    )
    weather_warnings: list[str] | None = Field(
        default=None,
        description="Weather-related warnings (e.g., ['雾天注意安全', '建议带伞'])",
    )
    emoji_summary: str = Field(
        ...,
        max_length=50,
        description="Emoji summary of the recommendation (e.g., '🧥🧣❄️')",
    )


class WeatherSnapshot(BaseModel):
    """Weather data snapshot at recommendation time."""

    city: str
    temperature: float
    weather: str
    humidity: float
    wind_direction: str
    wind_power: str
    report_time: str


class RecommendationCreate(BaseModel):
    """Schema for creating recommendations (1-3 days)."""

    city: str = Field(..., min_length=1, description="City name or AD code")
    days: int = Field(
        default=1, ge=1, le=3, description="Number of days to generate (1-3)"
    )


class RecommendationResponse(BaseModel):
    """Response schema for recommendation."""

    id: str
    user_id: int
    city: str
    weather_data: dict[str, Any]
    clothing_items: list[str]
    advice: str
    weather_warnings: list[str] | None
    emoji_summary: str
    cached: bool = Field(
        default=False, description="Whether the recommendation is from cache"
    )
    cost_estimate: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    """Response schema for list of recommendations."""

    items: list[RecommendationResponse]
    total: int
    limit: int
    offset: int


# Multi-day recommendation schemas for admin use


class AdminGenerateMultiDayRequest(BaseModel):
    """Request schema for admin to generate multi-day recommendations for a user."""

    user_id: int = Field(
        ..., description="Target user ID to generate recommendations for"
    )
    city_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit city AD code"
    )
    send_email: bool = Field(
        default=False, description="Automatically send email after generation"
    )


class DailyRecommendation(BaseModel):
    """Single day recommendation in multi-day response."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    date_label: str = Field(..., description="Chinese label (今天, 明天, 后天)")
    recommendation: RecommendationResponse = Field(
        ..., description="Full recommendation object"
    )
    weather_summary: str = Field(
        ..., description="Brief weather summary (e.g., '晴天，最高15°C，最低5°C')"
    )


class UserBasicInfo(BaseModel):
    """Basic user info for multi-day response."""

    id: int
    email: str
    full_name: str | None


class MultiDayRecommendationResponse(BaseModel):
    """Response schema for multi-day recommendations."""

    user: UserBasicInfo = Field(..., description="Target user information")
    city: str = Field(..., description="City name")
    city_code: str = Field(..., description="City AD code")
    recommendations: list[DailyRecommendation] = Field(
        ..., description="List of daily recommendations (3 items)"
    )
    email_sent: bool = Field(..., description="Whether email was sent")
    generated_at: datetime = Field(
        ..., description="Timestamp when recommendations were generated"
    )
