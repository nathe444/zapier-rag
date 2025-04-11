from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    filename: str
    content_type: str
    size: float

class DocumentCreate(DocumentBase):
    bot_id: str

class DocumentInDB(DocumentBase):
    id: str
    bot_id: str
    created_at: datetime

    class Config:
        orm_mode = True

# Alias for response model
Document = DocumentInDB