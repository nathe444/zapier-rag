from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.schemas.bot import Bot  # Add this import
from app.services.bot_service import BotService
from typing import List
import uuid
from datetime import datetime
from app.database.models import User as UserModel

router = APIRouter()

@router.post("/users", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if username or email already exists
    existing_user = db.query(UserModel).filter(
        (UserModel.username == user.username) | (UserModel.email == user.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = UserModel(
        id=user_id,
        username=user.username,
        email=user.email,
        hashed_password=user.password,  # In a real app, you would hash this password
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a user by ID"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's properties"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update provided fields
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

# Change from "/users/{user_id}/bots" to "/{user_id}/bots"
@router.get("/{user_id}/bots", response_model=List[Bot])
async def get_user_bots(user_id: str, db: Session = Depends(get_db)):
    """Get all bots for a user"""
    bot_service = BotService(db)
    return bot_service.get_user_bots(user_id)