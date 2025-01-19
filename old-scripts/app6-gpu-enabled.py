import os
import torch
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import time

def main():
    try:
        # Initialize CUDA device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            torch.cuda.set_device(0)
            torch.backends.cudnn.benchmark = True
        
        print(f"Using device: {'GPU: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

        # Load PDF
        print("Starting PDF loading...")
        pdf_paths = ["C:\\Users\\menuk\\Desktop\\BOT-4\\Karbon User Guide.pdf"]
        data = []
        for pdf_path in pdf_paths:
            loader = PyPDFLoader(pdf_path)
            data.extend(loader.load())
        print(f"Total number of pages loaded: {len(data)}")

        # Optimize chunk size for GPU memory
        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=384)
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # Initialize embeddings with GPU support
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': device},
            encode_kwargs={
                'device': device,
                'batch_size': 16,  # Optimized for RTX 3050 Ti
                'normalize_embeddings': True
            }
        )
        print("Embeddings initialized successfully")

        # Create Vector Store
        print("Creating vector store...")
        vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
        print("Vector store created successfully")

        # Optimized retriever
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={
                "k": 4,
                "fetch_k": 20
            }
        )
        print("Retriever created successfully")

        # Initialize Llama with GPU support
        print("Initializing Llama 3 model...")
        llm = OllamaLLM(
            model="llama3.1:8b",
            temperature=0.5,
            model_kwargs={
                "device": device,
                "num_threads": 6  # Optimized for Ryzen 7
            }
        )
        print("Llama 3 model initialized successfully")

        # Create Chain
        print("Creating chain...")
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are a helpful assistant. Use the following context to answer the question. Be concise and accurate.
Context: {context}
Question: {question}
Answer: Let me help you with that."""
        )
        
        llm_chain = prompt | llm | StrOutputParser()
        rag_chain = {"context": retriever, "question": RunnablePassthrough()} | llm_chain
        print("Chain created successfully")

        # Query loop with basic GPU optimization
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() == 'quit':
                break
            
            print("\nProcessing...")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Clear GPU cache before each query
            
            start_time = time.time()
            response = rag_chain.invoke(question)
            end_time = time.time()
            elapsed_time = end_time - start_time    
            
            print(f"\nTime taken: {elapsed_time:.2f} seconds")
            print("\nResponse:", response)

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()