import os
import torch
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from functools import lru_cache
from chromadb.config import Settings
from typing import Dict, Optional
from langchain_core.callbacks import BaseCallbackHandler

class StreamingStdOutCallbackHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(token, end="", flush=True)

def main():
    try:
        # Check if GPU is available
        is_gpu_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if is_gpu_available else "CPU"
        print(f"Using device: {'GPU: ' + device_name if is_gpu_available else 'CPU'}")

        # PDF Loading and Document Splitting remain the same...
        print("Starting PDF loading...")
        pdf_paths = ["Karbon User Guide.pdf"]
        data = []
        for pdf_path in pdf_paths:
            loader = PyPDFLoader(pdf_path)
            data.extend(loader.load())
        print(f"Total number of pages loaded: {len(data)}")

        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # Initialize Embeddings
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        print("Embeddings initialized successfully")

        # Vector Store setup
        print("Initializing vector store...")
        vectorstore_dir = "vectorstore_dir"
        if os.path.exists(vectorstore_dir):
            print("Loading existing vector store...")
            vectorstore = Chroma(persist_directory=vectorstore_dir, embedding_function=embeddings)
        else:
            print("Creating new vector store...")
            vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=vectorstore_dir)
            print("Saving vector store...")
            vectorstore.persist()
        print("Vector store is ready")

        # Create Retriever
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        print("Retriever created successfully")

        # Initialize Llama with streaming
        print("Initializing Llama 3 model...")
        llm = OllamaLLM(
            model="llama3:latest",
            temperature=0.3,
            streaming=True,
        )
        print("Llama 3 model initialized successfully")

        # Create Chain
        print("Creating chain...")
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful assistant. Use the following context to answer the question concisely.

Context: {context}

Question: {question}

Answer:"""
        )
        
        llm_chain = prompt | llm | StrOutputParser()
        rag_chain = {"context": retriever, "question": RunnablePassthrough()} | llm_chain
        print("Chain created successfully")

        # Create streaming callback handler
        streaming_handler = StreamingStdOutCallbackHandler()

        print("\nBot is ready! Ask your questions or type 'quit' to exit.")
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() == 'quit':
                break
            
            print("\nProcessing...\n")
            start_time = time.time()
            
            # Stream the response
            response = rag_chain.invoke(question, callbacks=[streaming_handler])
            
            elapsed_time = time.time() - start_time
            print(f"\n\nTime taken: {elapsed_time:.2f} seconds")

        print("\nProcess completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()