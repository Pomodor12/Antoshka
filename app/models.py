from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base
from datetime import datetime

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    guests = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    origin_chat_id = Column(String, nullable=True)  # could be bigint
    posted_to_chats = Column(JSONB, nullable=True)  # list
    created_at = Column(DateTime, default=datetime.utcnow)
    notify_weekly_sent = Column(Boolean, default=False)
    notify_24h_sent = Column(Boolean, default=False)
    notify_immediate_sent = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
