from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, Integer, String, DateTime, func, text
from ..base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, nullable=False)
    username = Column(String(30), unique=True, nullable=False)
    email_id = Column(String(50), unique=True, nullable=False)
    password = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# from enum import Enum
    # role = Column(Enum("user", "admin", name="user_roles"), default="user", nullable=False)
    # title = Column(String(108), index=True)
    # content = Column(String(255), index=True)