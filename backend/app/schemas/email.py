"""Email-related schemas."""

from datetime import datetime, time
from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailPreferencesResponse(BaseModel):
    """Response schema for email preferences."""

    email_notifications_enabled: bool
    email_send_time: time | None = None
    email_additional_recipients: List[str] | None = None
    email_preferred_city: str | None = None


class EmailPreferencesUpdate(BaseModel):
    """Schema for updating email preferences."""

    email_notifications_enabled: bool | None = None
    email_send_time: str | None = Field(
        None, description="Time in HH:MM format (24-hour)"
    )
    email_additional_recipients: List[str] | None = None
    email_preferred_city: str | None = None

    @field_validator("email_send_time")
    @classmethod
    def validate_send_time(cls, v: str | None) -> time | None:
        """Validate and parse send time."""
        if v is None:
            return None
        try:
            hour, minute = map(int, v.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("Time must be in HH:MM format (24-hour)")
            return time(hour, minute)
        except (ValueError, AttributeError) as e:
            raise ValueError("Time must be in HH:MM format (24-hour)") from e

    @field_validator("email_additional_recipients")
    @classmethod
    def validate_emails(cls, v: List[str] | None) -> List[str] | None:
        """Validate email addresses."""
        if v is None:
            return None
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        invalid_emails = [email for email in v if not re.match(pattern, email)]
        if invalid_emails:
            raise ValueError(f"Invalid email addresses: {', '.join(invalid_emails)}")
        return v


class EmailSendRequest(BaseModel):
    """Request schema for sending email."""

    city: str = Field(..., description="City AD code or name")
    recipient_emails: List[EmailStr] = Field(
        ..., description="List of email addresses to send to"
    )


class EmailDeliveryResult(BaseModel):
    """Result for a single email delivery."""

    recipient_email: str
    status: str  # "sent" or "failed"
    error_message: str | None = None


class EmailSendResponse(BaseModel):
    """Response schema for email send request."""

    success: bool
    message: str
    deliveries: List[EmailDeliveryResult]


class EmailLogResponse(BaseModel):
    """Response schema for email log entry."""

    id: int
    user_id: int
    recommendation_id: str | None
    recipient_email: str
    status: str
    sent_at: datetime
    error_message: str | None = None

    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    """Response schema for email log list."""

    total: int
    items: List[EmailLogResponse]
