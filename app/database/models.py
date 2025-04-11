from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with bots
    bots = relationship("Bot", back_populates="user")

class Bot(Base):
    __tablename__ = "bots"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    model_name = Column(String)
    temperature = Column(Float, default=0.7)
    llm_provider = Column(String, default="openai")
    user_id = Column(String, ForeignKey("users.id"))  # Add this foreign key
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="bots")
    
    # Relationship with documents
    documents = relationship("Document", back_populates="bot")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    content_type = Column(String)
    bot_id = Column(String, ForeignKey("bots.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with bot
    bot = relationship("Bot", back_populates="documents")