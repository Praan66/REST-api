# pg datatype for uuid
from sqlalchemy.dialects.postgresql import UUID
# py library use to generate uuid 
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content = Column(Text, nullable=False) #/text
    caption = Column(String(255), nullable=False)#/title
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="posts")
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan", order_by="PostMedia.order_index")
