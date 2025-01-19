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
        # 1. PDF Loading
        print("Starting PDF loading...")
        pdf_paths = ["Karbon User Guide.pdf"]
        data = []
        for pdf_path in pdf_paths:
            loader = PyPDFLoader(pdf_path)
            data.extend(loader.load())
        print(f"Total number of pages loaded: {len(data)}")

        # 2. Document Splitting
        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500)
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # 3. Initialize Embeddings
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        print("Embeddings initialized successfully")

        # 4. Create Vector Store
        print("Creating vector store...")
        vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
        print("Vector store created successfully")

        # 5. Create Retriever
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        print("Retriever created successfully")

        # 6. Initialize Llama 3 through Ollama
        print("Initializing Llama 3 model...")
        llm = OllamaLLM(
            model="llama3",
            temperature=0.5,
        )
        print("Llama 3 model initialized successfully")

        # 7. Create Chain
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

        # 8. Run Query
        print("Running query...")
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() == 'quit':
                break
            
            print("\nProcessing...")
            start_time = time.time()  # Record the start time
            response = rag_chain.invoke(question)
            end_time = time.time()
            elapsed_time = end_time - start_time    
            print(f"\nTime taken: {elapsed_time:.2f} seconds")
            print("\nResponse:", response)

        print("\nProcess completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()