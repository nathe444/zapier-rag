from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.pgvector import PGVector
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from typing import List, AsyncGenerator
import os
from langchain.prompts import PromptTemplate

class DocumentService:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.vector_store = None
        self.llm = ChatOpenAI(
            temperature=0.9,  # Increased temperature for more detailed responses
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        self.initialize_vector_store()

    def initialize_vector_store(self):
        try:
            # Try to load existing collection
            self.vector_store = PGVector.from_existing_index(
                embedding=self.embeddings,
                connection_string=self.connection_string,
                collection_name="document_embeddings"
            )
        except:
            # If collection doesn't exist, create new one
            self.vector_store = PGVector(
                connection_string=self.connection_string,
                embedding_function=self.embeddings,
                collection_name="document_embeddings"
            )
        
        # Initialize QA chain with vector store
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": 5}  # Increased from 3 to 5 for more context
            ),
            return_source_documents=True
        )

    def process_pdf(self, file_path: str) -> List[str]:
        # Process the new document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        
        # Clear existing vectors and add new ones
        self.vector_store.delete_collection()
        self.vector_store = PGVector.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            connection_string=self.connection_string,
            collection_name="document_embeddings"
        )
        
        # Reinitialize the QA chain with the new vector store
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),  # Increased from 3 to 5
            return_source_documents=True
        )
        
        return chunks

    async def get_streaming_answer(self, query: str, chat_history: List = None) -> AsyncGenerator[str, None]:
        if chat_history is None:
            chat_history = []
                
        formatted_history = [(h[0], h[1]) for h in chat_history]
        
        # Custom prompt template with more general instructions
        custom_prompt = PromptTemplate.from_template(
            """You are a helpful assistant. When answering questions, provide detailed information 
            based on the context provided.
            
            Context information is below.
            ---------------------
            {context}
            ---------------------
            
            Chat History: {chat_history}
            
            Question: {question}
            
            Answer the question based on the context information and chat history.
            When providing numerical information such as rates, percentages, or statistics, 
            always include the specific numbers and use bullet points for clarity.
            Ensure your answer is complete and comprehensive.
            If you don't know the answer, say that you don't know.
            """
        )
        
        # Create a streaming chain with custom prompt and increased token limit
        streaming_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(
                temperature=0.7,
                streaming=True,
                max_tokens=2000  # Increased token limit for more complete responses
            ),
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": 5}
            ),
            combine_docs_chain_kwargs={"prompt": custom_prompt},
            return_source_documents=True
        )
        
        # Use a non-streaming approach to get the complete answer first
        try:
            # Get complete response first (non-streaming)
            complete_response = await streaming_chain.ainvoke({
                "question": query,
                "chat_history": formatted_history
            })
            
            if "answer" in complete_response:
                # Then yield it chunk by chunk to maintain streaming appearance
                answer = complete_response["answer"]
                # Yield in chunks of approximately 20 characters
                chunk_size = 20
                for i in range(0, len(answer), chunk_size):
                    yield answer[i:i+chunk_size]
            else:
                yield "I apologize, but I couldn't generate a complete answer. Please try asking your question again."
        except Exception as e:
            print(f"Error generating response: {e}")
            yield "I apologize, but I encountered an error while generating the response. Please try again."