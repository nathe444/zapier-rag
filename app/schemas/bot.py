from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BotBase(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    llm_provider: str = "openai"

class BotCreate(BotBase):
    user_id: str

class BotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    llm_provider: Optional[str] = None

class BotInDB(BotBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Alias for response model
Bot = BotInDB