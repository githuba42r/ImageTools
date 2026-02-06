from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Image(Base):
    __tablename__ = "images"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    original_size = Column(Integer, nullable=False)
    current_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    current_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    format = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class History(Base):
    __tablename__ = "history"
    
    id = Column(String, primary_key=True, index=True)
    image_id = Column(String, ForeignKey("images.id"), nullable=False, index=True)
    operation_type = Column(String, nullable=False)
    operation_params = Column(Text, nullable=True)
    input_path = Column(String, nullable=False)
    output_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sequence = Column(Integer, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    image_id = Column(String, ForeignKey("images.id"), nullable=False)
    model = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    total_cost = Column(Float, default=0.0)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
