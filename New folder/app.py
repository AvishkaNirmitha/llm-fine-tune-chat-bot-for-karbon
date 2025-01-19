import google.generativeai as genai
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from typing import List, Tuple




class RAGSystem:
    def __init__(self, gemini_api_key: str):
        """Initialize the RAG system with Gemini API credentials"""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.document_chunks = []
        self.document_embeddings = None

    def process_pdf(self, pdf_path: str, chunk_size: int = 1000):
        """Extract text from PDF and split into chunks"""
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Split text into chunks
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        self.document_chunks = chunks
        self.document_embeddings = self.embedding_model.encode(chunks)

    def retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        """Retrieve k most relevant chunks for the query"""
        query_embedding = self.embedding_model.encode([query])[0]
        similarities = cosine_similarity([query_embedding], self.document_embeddings)[0]
        
        # Get indices of top k similar chunks
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        
        # Return chunks and their similarity scores
        return [(self.document_chunks[i], similarities[i]) for i in top_k_indices]

    async def generate_response(self, query: str) -> str:
        """Generate response using retrieved context and Gemini"""
        relevant_chunks = self.retrieve_relevant_chunks(query)
        
        # Construct prompt with context
        context = "\n\n".join([chunk for chunk, _ in relevant_chunks])
        prompt = f"""Context information is below.
        ---------------------
        {context}
        ---------------------
        Given the context information and no other information, answer the following query:
        {query}"""

        # Generate response using Gemini
        response = await self.model.generate_content(prompt)
        return response.text

# Example usage
async def main():
    # Initialize RAG system
    rag = RAGSystem(gemini_api_key="AIzaSyAY6Nw_43VLICeZY_gkUBTFLF9gtMt4khQ")
    
    # Process PDF document
    rag.process_pdf("Karbon User Guide.pdf")
    
    # Example query
    query = "What are the main points discussed in the document?"
    response = await rag.generate_response(query)
    print(f"Query: {query}\nResponse: {response}")

# Run the example
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())