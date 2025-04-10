from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from typing import List, Optional
from langchain.prompts import PromptTemplate

class BaseAgent:
    def __init__(
        self,
        bot_id: str,
        user_id: str,
        session_id: str,
        system_prompt: str = None,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        llm_provider: str = "openai"
        document_service=None
    ):
        self.bot_id = bot_id
        self.user_id = user_id
        self.session_id = session_id
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory()
        
        # Initialize conversation chain
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )
        
        # Initialize tools list
        self.tools = []
        self.document_service = document_service
        self.rag_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""Answer the question based on the following context:

Context:
{context}

Question:
{question}

Answer:"""
        )

    def add_tool(self, tool):
        """Add a tool to the agent."""
        self.tools.append(tool)
    
    def add_message_to_history(self, role: str, content: str):
        """Add a message to the conversation history."""
        if role == "user":
            self.memory.chat_memory.add_user_message(content)
        else:
            self.memory.chat_memory.add_ai_message(content)
    
    def get_conversation_history(self):
        """Get the conversation history."""
        return self.memory.chat_memory.messages
    
    def process_message(self, message: str) -> str:
        """
        Process a message from the user and return a response.
        
        Args:
            message: The message from the user
            
        Returns:
            The response from the agent
        """
        if self.document_service:
            # Get relevant documents
            relevant_docs = self.document_service.similarity_search(message)
            context = "\n\n".join(relevant_docs)
            
            # Create prompt with context
            prompt = self.rag_prompt.format(
                context=context,
                question=message
            )
        else:
            prompt = message

        # Add the user message to the history
        self.add_message_to_history("user", message)
        
        # Get response from conversation chain
        response = self.conversation.predict(input=prompt)
        
        # Add the assistant response to the history
        self.add_message_to_history("assistant", response)
        
        return response