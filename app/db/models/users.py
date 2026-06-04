from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, Integer, String, DateTime, func, text
from sqlalchemy.orm import relationship
from ..base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, nullable=False)
    username = Column(String(30), unique=True, nullable=False)
    email_id = Column(String(50), unique=True, nullable=False)
    role = Column(String(50), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    credential = relationship("User_tb", back_populates="user", uselist=False, cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")

# class User(Base):
#     __tablename__ = "users"
#     id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, nullable=False)
#     username = Column(String(30), unique=True, nullable=False)
#     email_id = Column(String(50), unique=True, nullable=False)
#     password = Column(String(120), nullable=False)
#     role = Column(String(50), default="user")
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
#     credential = relationship("User_tb", back_populates="user", uselist=False)

# from enum import Enum
    # role = Column(Enum("user", "admin", name="user_roles"), default="user", nullable=False)
    # title = Column(String(108), index=True)
    # content = Column(String(255), index=True)