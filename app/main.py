from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from dotenv import load_dotenv
from app.services.document_service import DocumentService
from app.api.api import api_router
from app.database.database import engine, Base
from app.database.models import User
from sqlalchemy.orm import Session
from sqlalchemy import text  # Add this import for the text() function
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# Drop all tables and recreate them with CASCADE option
with engine.connect() as connection:
    connection.execute(text("DROP TABLE IF EXISTS sessions, bots, users, documents CASCADE"))
    connection.commit()

# Create all tables
Base.metadata.create_all(bind=engine)

# Create a test user if it doesn't exist
def create_test_user():
    with Session(engine) as db:
        # Check if test user exists
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            # Create test user
            user_id = "test-user-id"  # Use the ID expected by the frontend
            new_user = User(
                id=user_id,
                username="testuser",
                email="test@example.com",
                hashed_password="password123",  # In a real app, this would be hashed
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_user)
            db.commit()
            print(f"Created test user with ID: {user_id}")

# Call the function to create test user
create_test_user()

# Initialize FastAPI app
app = FastAPI(title="Multi-Bot Chat System")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize document service
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
document_service = DocumentService(DATABASE_URL)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router

app = FastAPI(title="Bot API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(api_router, prefix="/api")

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[List[str]]] = []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/train.html", response_class=HTMLResponse)
async def train_page(request: Request):
    return templates.TemplateResponse("train.html", {"request": request})

# Update these routes to handle both path and query parameters
@app.get("/chat.html", response_class=HTMLResponse)
async def chat_page_query(request: Request, botId: Optional[str] = None):
    # Use the query parameter if provided
    return templates.TemplateResponse("chat.html", {"request": request, "bot_id": botId})

@app.get("/chat/{bot_id}", response_class=HTMLResponse)
async def chat_page_path(request: Request, bot_id: str):
    # Use the path parameter
    return templates.TemplateResponse("chat.html", {"request": request, "bot_id": bot_id})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save the uploaded file temporarily
    file_path = f"temp_{file.filename}"
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Process the PDF
        chunks = document_service.process_pdf(file_path)
        return {"message": f"Successfully processed PDF into {len(chunks)} chunks"}
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in document_service.get_streaming_answer(request.question, request.chat_history):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )