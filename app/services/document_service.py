from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.pgvector import PGVector
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from typing import List, AsyncGenerator
import os

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
            temperature=0.7,
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
                search_kwargs={"k": 3}
            ),
            return_source_documents=True
        )

    def process_pdf(self, file_path: str) -> List[str]:
        # Process new document without clearing existing embeddings
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        texts = self.text_splitter.split_documents(documents)
        self.vector_store.add_documents(texts)
        return [doc.page_content for doc in texts]

    async def get_streaming_answer(self, query: str, chat_history: List = None) -> AsyncGenerator[str, None]:
        if chat_history is None:
            chat_history = []
                
        formatted_history = [(h[0], h[1]) for h in chat_history]
        
        # Create a streaming chain
        streaming_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(
                temperature=0.7,
                streaming=True
            ),
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )
        
        async for chunk in streaming_chain.astream({
            "question": query,
            "chat_history": formatted_history
        }):
            if isinstance(chunk, dict) and "answer" in chunk:
                yield chunk["answer"]