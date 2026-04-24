from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func, text
from sqlalchemy.orm import relationship
from ...db.base import Base

class User_tb(Base):
    __tablename__ = "users_credentials"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, index=True, nullable=False)
    hashed_password = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="credential")
    
# class User_tb(Base):
#     __tablename__ = "users_credentials"
#     id = Column(UUID(as_uuid=True), ForeignKey("user.id"), primary_key=True, index=True, nullable=False)
#     username = Column(String(30), unique=True, nullable=False)
#     email_id = Column(String(50), unique=True, nullable=False)
#     hashed_password = Column(String(120), nullable=False)
#     role = Column(String(50), default="user")
#     user = relationship("User", back_populates="credential")

# from enum import Enum
    # role = Column(Enum("user", "admin", name="user_roles"), default="user", nullable=False)
    # title = Column(String(108), index=True)
    # content = Column(String(255), index=True)