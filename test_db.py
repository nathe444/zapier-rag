from app.database.database import init_db
from app.database.models import Bot, User, Base
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import os
from dotenv import load_dotenv

load_dotenv()

def test_database():
    # Create connection URL object
    url = URL.create(
        "postgresql",
        username=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME')
    )
    
    # Create engine using URL object
    engine = create_engine(url)
    
    # Create tables first
    Base.metadata.create_all(bind=engine)
    
    # Initialize database (for vector extension)
    init_db()
    
    with Session(engine) as session:
        # Create test bot
        test_bot = Bot(
            id="test-bot-1",
            name="Test Bot",
            description="A test bot",
            system_prompt="You are a helpful assistant."
        )
        
        # Create test user
        test_user = User(
            id="test-user-1",
            name="Test User",
            email="test@example.com"
        )
        
        # Add to database
        session.add(test_bot)
        session.add(test_user)
        session.commit()
        
        print("Test data created successfully!")

if __name__ == "__main__":
    test_database()