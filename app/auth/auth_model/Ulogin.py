from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func, text
from sqlalchemy.orm import relationship
from app.db.base import Base

class User_tb(Base):
    __tablename__ = "users_credentials"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, index=True, nullable=False)
    hashed_password = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="credential")
    