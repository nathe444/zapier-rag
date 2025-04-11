from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.bot_service import BotService
from app.services.document_service import DocumentService
from typing import Dict, List, Any, Optional
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    chat_history: Optional[List[List[str]]] = []

# Add a GET endpoint to handle the initial connection
@router.get("/{bot_id}")
async def get_chat_info(bot_id: str, db: Session = Depends(get_db)):
    """Get information about a chat bot"""
    bot_service = BotService(db)
    bot = bot_service.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return {"bot_id": bot_id, "name": bot.name, "status": "ready"}

@router.post("/{bot_id}")
async def chat_with_bot(
    bot_id: str,
    chat_request: ChatMessage,
    db: Session = Depends(get_db)
):
    """Send a message to a bot and get a response"""
    # Check if bot exists
    bot_service = BotService(db)
    bot = bot_service.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Initialize document service
    connection_string = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    document_service = DocumentService(connection_string)
    
    # Create a streaming response
    async def generate():
        try:
            async for chunk in document_service.generate_response(
                bot_id=bot_id,
                query=chat_request.message,
                chat_history=chat_request.chat_history,
                system_prompt=bot.system_prompt
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Send end message
            yield f"data: {json.dumps({'end': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )