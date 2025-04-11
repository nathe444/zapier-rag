from sqlalchemy.orm import Session
from app.database.models import Bot, User
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class BotService:
    def __init__(self, db: Session):
        self.db = db
        
    def create_bot(self, user_id: str, name: str, description: str = None, 
                  system_prompt: str = None, model_name: str = "gpt-3.5-turbo", 
                  temperature: float = 0.7, llm_provider: str = "openai") -> Bot:
        """Create a new bot for a user"""
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
            
        # Create new bot
        bot_id = str(uuid.uuid4())
        new_bot = Bot(
            id=bot_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            llm_provider=llm_provider,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(new_bot)
        self.db.commit()
        self.db.refresh(new_bot)
        
        return new_bot
        
    def get_bot(self, bot_id: str) -> Optional[Bot]:
        """Get a bot by ID"""
        return self.db.query(Bot).filter(Bot.id == bot_id).first()
        
    def get_user_bots(self, user_id: str) -> List[Bot]:
        """Get all bots for a user"""
        return self.db.query(Bot).filter(Bot.user_id == user_id).all()
        
    def update_bot(self, bot_id: str, **kwargs) -> Optional[Bot]:
        """Update a bot's properties"""
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return None
            
        # Update provided fields
        for key, value in kwargs.items():
            if hasattr(bot, key):
                setattr(bot, key, value)
                
        bot.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(bot)
        
        return bot
        
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot"""
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return False
            
        self.db.delete(bot)
        self.db.commit()
        
        return True