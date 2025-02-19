# rag_engine.py

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from typing import Dict, Any
import tiktoken
import time
import os

from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()



# Token limits configuration
MAX_PROMPT_TOKENS = 3072
RESPONSE_TOKEN_BUFFER = 1024

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
        loader = PyPDFLoader("C:\\Users\\menuk\\Desktop\\karbon_bot\\Menuka_Changers\\Testing_PDF's\\sampel_1.pdf")
        data.extend(loader.load())

        # 2. Document Splitting
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=10)
        self.docs = text_splitter.split_documents(data)

        # 3. Initialize Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        # 4. Create Vector Store
        self.vectorstore = Chroma.from_documents(documents=self.docs, embedding=self.embeddings)

        # 5. Create Retriever
        self.retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

        # 6. Initialize Llama 3 through Groq
        self.llm = ChatGroq(
            temperature=0.8,
            groq_api_key=os.getenv('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'),
            model_name="llama-3.1-8b-instant"
        )

        # 7. Create Chain
        self.template = """
You are a helpful assistant. Use the following karbon user guide to answer the question. Be concise and accurate. dont answer anything out of your karbon user guide.

Context: {context}

Question: {question}

Answer: Let me help you with that."""
        
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.template
        )
        
        llm_chain = self.prompt | self.llm | StrOutputParser()
        self.rag_chain = {"context": self.retriever, "question": RunnablePassthrough()} | llm_chain

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
        prompt_tokens = count_tokens(self.template.format(context=context, question=question))
        
        # Verify we're within limits
        if prompt_tokens > MAX_PROMPT_TOKENS:
            raise ValueError(f"Total prompt tokens ({prompt_tokens}) exceeds limit ({MAX_PROMPT_TOKENS})")
        
        # Get response and count its tokens
        response = self.rag_chain.invoke(question)
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
    

