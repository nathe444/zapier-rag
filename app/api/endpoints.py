from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Bot, User, Session as ChatSession
from app.agents.base_agent import BaseAgent
from typing import Dict, Any
import uuid
import os
from fastapi import UploadFile, File
from tempfile import NamedTemporaryFile

router = APIRouter()

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Save uploaded file temporarily
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file.flush()
        
        try:
            # Process the document
            document_service = DocumentService(DATABASE_URL)
            chunks = document_service.process_pdf(temp_file.name)
            
            return {"message": f"Successfully processed {len(chunks)} chunks"}
        finally:
            os.unlink(temp_file.name)

@router.post("/chat")
async def chat_endpoint(
    bot_id: str,
    user_id: str,
    message: str,
    session_id: str = None,
    db: Session = Depends(get_db)
):
    # Get bot and user
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not bot or not user:
        raise HTTPException(status_code=404, detail="Bot or user not found")
    
    # Get or create session
    if not session_id:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            id=session_id,
            bot_id=bot_id,
            user_id=user_id
        )
        db.add(session)
        db.commit()
    else:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    
    # Initialize document service
    document_service = DocumentService(DATABASE_URL)
    
    # Initialize agent with document service
    agent = BaseAgent(
        bot_id=bot_id,
        user_id=user_id,
        session_id=session_id,
        system_prompt=bot.system_prompt,
        model_name=bot.model_name,
        temperature=bot.temperature,
        llm_provider=bot.llm_provider,
        document_service=document_service
    )
    
    # Process message
    response = agent.process_message(message)
    
    # Update session messages
    session.messages = session.messages + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response}
    ]
    db.commit()
    
    return {
        "session_id": session_id,
        "response": response
    }