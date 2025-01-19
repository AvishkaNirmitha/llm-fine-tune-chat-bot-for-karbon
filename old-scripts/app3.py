from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from transformers import pipeline
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import torch

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
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500)  # Reduced chunk size
        docs = text_splitter.split_documents(data)
        print(f"Total number of chunks: {len(docs)}")

        # 3. Initialize Embeddings
        print("Initializing embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"  # Smaller embedding model
        )
        print("Embeddings initialized successfully")

        # 4. Create Vector Store
        print("Creating vector store...")
        vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
        print("Vector store created successfully")

        # 5. Create Retriever
        print("Creating retriever...")
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})  # Reduced number of retrieved chunks
        print("Retriever created successfully")


        # retrieverDocs=retriever.invoke("what is the trading ")
        # print(
        #   retrieverDocs
        #     )
        # print(len(retrieverDocs))

        # return

        # 6. Initialize Language Model
        print("Initializing language model...")
        model_id = "microsoft/phi-2"  # Much smaller model suitable for CPU
        text_generation_pipeline = pipeline(
            "text-generation",
            model=model_id,
            max_new_tokens=256,  # Reduced output length
            device="cpu"
        )
        print("Language model initialized successfully")

        # 7. Create Chain
        print("Creating chain...")
        llm = HuggingFacePipeline(pipeline=text_generation_pipeline)
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
Based on the following context, please answer the question concisely:
Context: {context}
Question: {question}
Answer:"""
        )
        
        llm_chain = prompt | llm | StrOutputParser()
        rag_chain = {"context": retriever, "question": RunnablePassthrough()} | llm_chain
        print("Chain created successfully")

        # 8. Run Query
        print("Running query...")



        # question = "What is discussed in these documents?"
        # response = rag_chain.invoke(question)

        question = input("Enter your question: ")
        response = rag_chain.invoke(question)

        print("\nResponse:", response)

        print("\nProcess completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()