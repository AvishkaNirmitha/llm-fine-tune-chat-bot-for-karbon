from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import google.generativeai as genai
import os

def main():
    try:
        # Set your Google API key
        os.environ['GOOGLE_API_KEY'] = 'AIzaSyAY6Nw_43VLICeZY_gkUBTFLF9gtMt4khQ'
        
        # 1. PDF Loading
        print("Starting PDF loading...")
        pdf_path = "Karbon User Guide.pdf"  
        loader = PyPDFLoader(pdf_path)
        data = loader.load()
        print(f"Total number of pages loaded: {len(data)}")

        # 2. Document Splitting
        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # 3. Initialize Embeddings
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        print("Embeddings initialized successfully")

        # 4. Create Vector Store
        print("Creating vector store...")
        vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
        print("Vector store created successfully")

        # 5. Create Retriever
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        print("Retriever created successfully")

        # 6. Initialize Gemini
        print("Initializing Gemini...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.3,
            convert_system_message_to_human=True
        )
        print("Gemini initialized successfully")

        # 7. Create Chain
        print("Creating chain...")
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are a helpful assistant. Use the following context to answer the question accurately and concisely:
Context: {context}
Question: {question}
Answer: """
        )
        
        llm_chain = prompt | llm | StrOutputParser()
        rag_chain = {"context": retriever, "question": RunnablePassthrough()} | llm_chain
        print("Chain created successfully")

        # 8. Run Query
        print("\nRunning query...")
        # question = "What is discussed in these documents?"
        # question = "What is the trading ?"
        # response = rag_chain.invoke(question)
        # print("\nResponse:", response)

        while True:

            question = input("Enter your question: ")
            response = rag_chain.invoke(question)

            print("\nResponse:", response)


            print("\nProcess completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()