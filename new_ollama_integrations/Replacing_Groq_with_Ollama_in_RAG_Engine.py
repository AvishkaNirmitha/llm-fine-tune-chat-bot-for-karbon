# rag_engine.py

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate
from typing import Dict, Any
import tiktoken
import time
import os
import requests
import json

from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Token limits configuration
MAX_PROMPT_TOKENS = 3072
RESPONSE_TOKEN_BUFFER = 1024
# Ollama API URL
OLLAMA_URL = "http://localhost:11434/api/generate"

def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def truncate_context(context: str, max_tokens: int) -> str:
    """Truncate context to fit within max tokens while keeping complete sentences."""
    if count_tokens(context) <= max_tokens:
        return context
    
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(context)
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)
    
    last_period = truncated_text.rfind('.')
    if last_period > 0:
        truncated_text = truncated_text[:last_period + 1]
    
    return truncated_text

class OllamaLLM:
    def __init__(self, model_name="qwen2.5:3b", temperature=0.5, max_tokens=512):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})

    def invoke(self, prompt):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        }
        
        try:
            response = self.session.post(OLLAMA_URL, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"Error from Ollama API: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error connecting to Ollama: {e}")

class QueryResult:
    def __init__(self, answer: str, token_info: Dict[str, int], timing: float, context: str):
        self.answer = answer
        self.token_info = token_info
        self.timing = timing
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "token_info": self.token_info,
            "timing_seconds": self.timing,
            "context_used": self.context
        }

class RAGQueryEngine:
    def __init__(self):
        self.setup_chain()

    def setup_chain(self):
        # 1. PDF Loading
        data = []
        loader = PyPDFLoader(r"C:\Users\Nuwan\OneDrive\Desktop\ML\Spera ML\Task16_rag\llm-fine-tune-chat-bot-for-karbon\new_ollama_integrations\Testing_PDF\sigalovada.pdf")
        data.extend(loader.load())

        # 2. Document Splitting
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=10)
        self.docs = text_splitter.split_documents(data)

        # 3. Initialize Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        # 4. Create Vector Store
        self.vectorstore = Chroma.from_documents(documents=self.docs, embedding=self.embeddings)

        # 5. Create Retriever
        self.retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 1})

        # 6. Initialize Ollama LLM (replacing Groq)
        self.llm = OllamaLLM(
            model_name="qwen2.5:3b",
            temperature=0.8,
            max_tokens=512
        )

        # 7. Create Chain
        self.template = """
You a helpful AI assistant specializing in the Sigalovada Sutta.
 Be concise, accurate, and give short answers.

Context: {context}

Question: {question}

Answer: Let me help you with that."""
        
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.template
        )

    def query(self, question: str) -> QueryResult:
        """
        Process a query and return structured results including the answer, token usage, and timing.
        """
        start_time = time.time()
        
        # Get retrieved documents
        retrieved_docs = self.retriever.get_relevant_documents(question)
        context = "\n".join(doc.page_content for doc in retrieved_docs)
        
        # Count initial tokens
        question_tokens = count_tokens(question)
        template_tokens = count_tokens(self.template.replace("{context}", "").replace("{question}", ""))
        available_context_tokens = MAX_PROMPT_TOKENS - question_tokens - template_tokens
        
        # Truncate context if necessary
        if count_tokens(context) > available_context_tokens:
            context = truncate_context(context, available_context_tokens)
        
        # Count final tokens
        context_tokens = count_tokens(context)
        final_prompt = self.template.format(context=context, question=question)
        prompt_tokens = count_tokens(final_prompt)
        
        # Verify we're within limits
        if prompt_tokens > MAX_PROMPT_TOKENS:
            raise ValueError(f"Total prompt tokens ({prompt_tokens}) exceeds limit ({MAX_PROMPT_TOKENS})")
        
        # Get response directly from Ollama
        response = self.llm.invoke(final_prompt)
        response_tokens = count_tokens(response)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Compile token information
        token_info = {
            "question_tokens": question_tokens,
            "context_tokens": context_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
            "max_prompt_tokens": MAX_PROMPT_TOKENS,
            "max_total_tokens": MAX_PROMPT_TOKENS+RESPONSE_TOKEN_BUFFER
        }
        
        return QueryResult(response, token_info, elapsed_time, context)