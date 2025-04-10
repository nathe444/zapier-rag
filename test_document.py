from app.services.document_service import DocumentService
import os
from dotenv import load_dotenv

load_dotenv()

def test_document_ingestion():
    DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    document_service = DocumentService(DATABASE_URL)
    
    pdf_path = "test_documents/sample.pdf"
    
    try:
        # Process the PDF
        chunks = document_service.process_pdf(pdf_path)
        print(f"Successfully processed PDF into {len(chunks)} chunks")
        
        # Test conversational QA
        questions = [
            "What is software engineering?",
            "What are some reasons why software projects fail?",
            "Can you explain more about agile methods?"
        ]
        
        chat_history = []
        for question in questions:
            print(f"\nQuestion: {question}")
            result = document_service.get_answer(question, chat_history)
            print("\nAnswer:", result["answer"])
            chat_history.append((question, result["answer"]))
            
    except Exception as e:
        print(f"Error during testing: {str(e)}")

if __name__ == "__main__":
    test_document_ingestion()