from fastapi import APIRouter
from app.api.routes import users, bots, chat

api_router = APIRouter()

# Include routers with proper prefixes
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(bots.router, prefix="/bots", tags=["bots"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])