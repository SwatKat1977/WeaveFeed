import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class AuthProvider(Base):
    __tablename__ = "auth_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),
                     ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    provider = Column(String(32), nullable=False)      # e.g. "google"
    provider_uid = Column(String(255), nullable=False) # unique provider ID
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_provider_uid"),
    )
