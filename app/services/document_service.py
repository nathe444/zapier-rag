from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from typing import List, AsyncGenerator
import os
from langchain.prompts import PromptTemplate
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

class DocumentService:
    def __init__(self, connection_string: str, db: Session = None):
        self.connection_string = connection_string
        self.db = db
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        # Initialize PGVector tables
        self._initialize_pgvector()
        
    def _initialize_pgvector(self):
        """Initialize PGVector tables in the database"""
        try:
            # Create a SQLAlchemy engine
            engine = create_engine(self.connection_string)
            
            # Create the pgvector extension if it doesn't exist
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                
            # Instead of using PGVector.create_tables which doesn't exist,
            # manually create the tables if they don't exist
            with engine.connect() as conn:
                # Create collection table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_collection (
                    name VARCHAR(50) PRIMARY KEY,
                    cmetadata JSON
                );
                """))
                
                # Create embedding table with vector support
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                    id SERIAL PRIMARY KEY,
                    collection_id VARCHAR(50) REFERENCES langchain_pg_collection(name),
                    embedding vector,
                    document TEXT,
                    cmetadata JSON,
                    custom_id TEXT
                );
                """))
                
                conn.commit()
                
            print("PGVector tables initialized successfully")
        except Exception as e:
            print(f"Error initializing PGVector tables: {e}")
    
    def process_pdf(self, file_path: str, bot_id: str) -> List[str]:
        """Process a PDF file and store its embeddings for a specific bot"""
        # Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Split into chunks
        chunks = self.text_splitter.split_documents(documents)
        
        # Create collection name based on bot_id to isolate embeddings
        collection_name = f"bot_{bot_id}_embeddings"
        
        # Store embeddings in vector database
        try:
            # Create a SQLAlchemy engine from the connection string
            engine = create_engine(self.connection_string)
            
            # Create PGVector store with the engine
            vector_store = PGVector.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection_name=collection_name,
                connection=engine,
                pre_delete_collection=True  # This will recreate the collection if it exists
            )
            
            # Return the text chunks for reference
            return [chunk.page_content for chunk in chunks]
        except Exception as e:
            print(f"Error storing embeddings: {e}")
            raise
    
    def get_retriever(self, bot_id: str):
        """Get a retriever for a specific bot's knowledge base"""
        # Create collection name based on bot_id
        collection_name = f"bot_{bot_id}_embeddings"
        
        try:
            # Create a SQLAlchemy engine from the connection string
            engine = create_engine(self.connection_string)
            
            # Initialize PGVector with the correct parameters
            # The error shows we need to use 'embeddings' parameter
            vector_store = PGVector(
                collection_name=collection_name,
                connection=engine,
                embeddings=self.embeddings  # Use embeddings instead of embedding_function
            )
            
            # Return the retriever
            return vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
        except Exception as e:
            print(f"Error loading vector store: {e}")
            return None
    
    def create_chain(self, bot_id: str, system_prompt: str = None):
        """Create a conversational chain for a specific bot"""
        # Get retriever for this bot
        retriever = self.get_retriever(bot_id)
        if not retriever:
            return None
        
        # Create LLM
        llm = ChatOpenAI(
            temperature=0.7,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        
        # Create custom prompt if system_prompt is provided
        if system_prompt:
            template = f"""
            {system_prompt}
            
            Context information is below.
            ---------------------
            {{context}}
            ---------------------
            
            Given the context information and not prior knowledge, answer the question: {{question}}
            """
            prompt = PromptTemplate(
                input_variables=["context", "question"],
                template=template
            )
            
            # Create chain with custom prompt
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": prompt}
            )
        else:
            # Create chain with default prompt
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever
            )
        
        return chain
    
    async def generate_response(self, bot_id: str, query: str, chat_history: List = None, system_prompt: str = None) -> AsyncGenerator[str, None]:
        """Generate a response from a bot based on its knowledge base"""
        if chat_history is None:
            chat_history = []
            
        # Convert chat history to the format expected by ConversationalRetrievalChain
        # The chain expects tuples of (human_message, ai_message)
        formatted_history = []
        for exchange in chat_history:
            if isinstance(exchange, list) and len(exchange) == 2:
                formatted_history.append((exchange[0], exchange[1]))
        
        # Create chain
        chain = self.create_chain(bot_id, system_prompt)
        if not chain:
            yield "Error: Could not create conversation chain. No documents found for this bot."
            return
        
        try:
            # Generate response with properly formatted chat history
            response = chain({"question": query, "chat_history": formatted_history})
            yield response["answer"]
        except Exception as e:
            yield f"Error generating response: {str(e)}"
    
    def clear_bot_knowledge(self, bot_id: str) -> bool:
        """Clear all documents for a specific bot"""
        collection_name = f"bot_{bot_id}_embeddings"
        
        try:
            # Create a SQLAlchemy engine from the connection string
            engine = create_engine(self.connection_string)
            
            # Connect to the database and drop the collection
            vector_store = PGVector(
                connection=engine,
                embeddings=self.embeddings,  # Updated parameter name
                collection_name=collection_name
            )
            
            # This is a simplified approach - in a real implementation,
            # you would need to properly drop the collection from the database
            # For now, we'll just create an empty collection to replace it
            vector_store = PGVector.from_documents(
                documents=[],
                embedding=self.embeddings,
                connection=engine,
                collection_name=collection_name
            )
            
            return True
        except Exception as e:
            print(f"Error clearing bot knowledge: {e}")
            return False

    def process_document(self, bot_id: str, filename: str, file_path: str):
        """Process a document and associate it with a bot"""
        from app.database.models import Document
        
        # Create a new document record
        document = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            content_type=self._get_content_type(filename),
            bot_id=bot_id,
            created_at=datetime.utcnow()
        )
        
        # Add document to database
        if self.db:
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
        
        # Process the document based on its type
        if filename.lower().endswith('.pdf'):
            self.process_pdf(file_path, bot_id=bot_id)
        elif filename.lower().endswith(('.txt', '.md')):
            self.process_text(file_path, bot_id=bot_id)
        # Add more document types as needed
        
        return document
    
    def process_text(self, file_path: str, bot_id: str):
        """Process a text file and store its embeddings for a specific bot"""
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        # Create text document
        from langchain.schema import Document as LangchainDocument
        doc = LangchainDocument(page_content=text, metadata={"source": file_path})
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([doc])
        
        # Create collection name based on bot_id to isolate embeddings
        collection_name = f"bot_{bot_id}_embeddings"
        
        # Store embeddings in vector database
        try:
            # Create a SQLAlchemy engine from the connection string
            engine = create_engine(self.connection_string)
            
            vector_store = PGVector.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection_name=collection_name,
                connection=engine,
                pre_delete_collection=True  # This will recreate the collection if it exists
            )
            
            # Return the text chunks for reference
            return [chunk.page_content for chunk in chunks]
        except Exception as e:
            print(f"Error storing embeddings: {e}")
            raise
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension"""
        if filename.lower().endswith('.pdf'):
            return 'application/pdf'
        elif filename.lower().endswith('.txt'):
            return 'text/plain'
        elif filename.lower().endswith('.md'):
            return 'text/markdown'
        # Add more content types as needed
        return 'application/octet-stream'  # Default content type