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

# Set environment variable to bypass the OpenMP runtime issue
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def main():
    try:
        # Initialize CUDA device and settings
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            torch.cuda.set_device(0)
            torch.backends.cudnn.benchmark = True  # Optimize for fixed input sizes
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"GPU Memory Available: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.2f} MB")
        else:
            print("Using CPU")

        # 1. PDF Loading
        print("Starting PDF loading...")
        pdf_paths = ["C:\\Users\\menuk\\Desktop\\BOT-4\\Karbon User Guide.pdf"]
        data = []
        for pdf_path in pdf_paths:
            loader = PyPDFLoader(pdf_path)
            data.extend(loader.load())
        print(f"Total number of pages loaded: {len(data)}")

        # 2. Document Splitting - Optimized chunk size for GPU
        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=384,  # Smaller chunks for GPU efficiency
            chunk_overlap=20  # Reduced overlap for memory efficiency
        )
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # 3. Initialize Embeddings with GPU support
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': device},
            encode_kwargs={
                'device': device,
                'batch_size': 16,  # Optimized for RTX 3050 Ti
                'normalize_embeddings': True,
                # 'show_progress_bar': True
            }
        )
        print("Embeddings initialized successfully")

        # 4. Create or Load Vector Store with GPU-optimized settings
        print("Initializing vector store...")
        vectorstore_dir = "vectorstore_dir"
        chroma_settings = Settings(
            anonymized_telemetry=False,
            is_persistent=True
        )
        
        if os.path.exists(vectorstore_dir):
            print("Loading existing vector store...")
            vectorstore = Chroma(
                persist_directory=vectorstore_dir, 
                embedding_function=embeddings,
                client_settings=chroma_settings
            )
        else:
            print("Creating new vector store...")
            vectorstore = Chroma.from_documents(
                documents=docs, 
                embedding=embeddings, 
                persist_directory=vectorstore_dir,
                client_settings=chroma_settings
            )
            print("Saving vector store...")
            vectorstore.persist()
        print("Vector store is ready")

        # 5. Create Retriever with optimized settings
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={
                "k": 3,
                # "fetch_k": 15  # Fetch more candidates for better selection
            }
        )
        print("Retriever created successfully")

        # 6. Initialize Llama with GPU support
        print("Initializing Llama 3 model...")
        llm = OllamaLLM(
            model="llama3.1:8b",
            temperature=0.3,
            model_kwargs={
                "device": device,
                "num_threads": 6,  # Optimized for Ryzen 7
            }
        )
        print("Llama 3 model initialized successfully")

        # 7. Create Chain
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

        # 8. Run Query with Caching and GPU Memory Management
        @lru_cache(maxsize=50)
        def cached_response(question):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Clear GPU cache before each query
            return rag_chain.invoke(question)

        print("\nBot is ready! Ask your questions or type 'quit' to exit.")
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() == 'quit':
                break
            
            print("\nProcessing...")
            start_time = time.time()
            
            try:
                response = cached_response(question)
                elapsed_time = time.time() - start_time
                print(f"\nResponse: {response}")
                print(f"Time taken: {elapsed_time:.2f} seconds")
            except Exception as query_error:
                print(f"Error processing query: {str(query_error)}")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()  # Clear GPU memory if there's an error

        print("\nProcess completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

if _name_ == "__main__":
    main()