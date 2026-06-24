# from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.db.models.enum.enum import MediaType

class PostMedia(Base):
    __tablename__ = "postmedia"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False)
    type = Column(Enum(MediaType), nullable=False)
    url = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    post = relationship("Post", back_populates="media")