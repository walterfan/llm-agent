"""Email log model for tracking email delivery status."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.base import Base


# Email send type constants
SEND_TYPE_MANUAL = "manual"
SEND_TYPE_SCHEDULED = "scheduled"
SEND_TYPE_ADMIN = "admin"


class EmailLog(Base):
    """Email log model for tracking email delivery status."""

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_id = Column(
        String(36),
        ForeignKey("recommendations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_email = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # "sent", "failed", "bounced"
    send_type = Column(
        String(20), nullable=True, index=True
    )  # "manual", "scheduled", "admin"
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    error_message = Column(Text, nullable=True)  # Error details if status is "failed"

    def __repr__(self) -> str:
        return f"<EmailLog(id={self.id}, user_id={self.user_id}, recipient={self.recipient_email}, status={self.status}, send_type={self.send_type})>"
