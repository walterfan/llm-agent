"""Permission model for RBAC system."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Permission(Base):
    """Permission model for fine-grained access control."""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(
        String(50), nullable=False, index=True
    )  # e.g., "user", "recommendation"
    action = Column(
        String(50), nullable=False
    )  # e.g., "create", "read", "update", "delete"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource}, action={self.action})>"
