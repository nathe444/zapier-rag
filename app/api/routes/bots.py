from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List  # Add this import
from app.database.database import get_db
from app.services.bot_service import BotService
from app.services.document_service import DocumentService
from app.schemas.bot import Bot, BotCreate, BotUpdate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define DATABASE_URL
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

router = APIRouter()

# Change from "/bots" to "/" since the prefix is added in api.py
@router.post("/", response_model=Bot)
async def create_bot(
    bot: BotCreate,
    db: Session = Depends(get_db)
):
    """Create a new bot for a user"""
    bot_service = BotService(db)
    try:
        new_bot = bot_service.create_bot(
            user_id=bot.user_id,
            name=bot.name,
            description=bot.description,
            system_prompt=bot.system_prompt,
            model_name=bot.model_name,
            temperature=bot.temperature,
            llm_provider=bot.llm_provider
        )
        return new_bot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Change from "/bots/{bot_id}" to "/{bot_id}"
@router.get("/{bot_id}", response_model=Bot)
async def get_bot(bot_id: str, db: Session = Depends(get_db)):
    """Get a bot by ID"""
    bot_service = BotService(db)
    bot = bot_service.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@router.get("/users/{user_id}/bots", response_model=List[Bot])
async def get_user_bots(user_id: str, db: Session = Depends(get_db)):
    """Get all bots for a user"""
    bot_service = BotService(db)
    return bot_service.get_user_bots(user_id)

# Change from "/bots/{bot_id}" to "/{bot_id}"
@router.put("/{bot_id}", response_model=Bot)
async def update_bot(
    bot_id: str,
    bot_update: BotUpdate,
    db: Session = Depends(get_db)
):
    """Update a bot's properties"""
    bot_service = BotService(db)
    
    # Build update dict with only provided values
    update_data = bot_update.dict(exclude_unset=True)
        
    updated_bot = bot_service.update_bot(bot_id, **update_data)
    if not updated_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return updated_bot

# Change from "/bots/{bot_id}" to "/{bot_id}"
@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, db: Session = Depends(get_db)):
    """Delete a bot"""
    bot_service = BotService(db)
    success = bot_service.delete_bot(bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"message": "Bot deleted successfully"}
# Change from "/bots/{bot_id}/documents" to "/{bot_id}/documents"
@router.post("/{bot_id}/documents", status_code=201)
async def upload_document_to_bot(
    bot_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document to a specific bot"""
    # Check if bot exists
    bot_service = BotService(db)
    bot = bot_service.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Save the uploaded file temporarily
    file_path = f"temp_{file.filename}"
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Process the document and associate it with the bot
        document_service = DocumentService(DATABASE_URL, db)
        document = document_service.process_document(
            bot_id=bot_id,
            filename=file.filename,
            file_path=file_path
        )
        
        return {"message": f"Document uploaded successfully", "document_id": document.id}
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# Also fix the clear knowledge endpoint
@router.post("/{bot_id}/clear-knowledge")
async def clear_bot_knowledge(
    bot_id: str,
    db: Session = Depends(get_db)
):
    """Clear all documents for a specific bot"""
    # Check if bot exists
    bot_service = BotService(db)
    bot = bot_service.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Initialize document service
    document_service = DocumentService(DATABASE_URL)  # Remove settings reference
    
    success = document_service.clear_bot_knowledge(bot_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear bot knowledge")
    
    return {"message": f"Knowledge base cleared for bot {bot_id}"}
