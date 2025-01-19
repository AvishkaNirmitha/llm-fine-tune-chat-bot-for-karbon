from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from transformers import pipeline
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import torch

# Load PDF file(s)
pdf_paths = [
    "Karbon User Guide.pdf",
]

# Initialize an empty list to store all documents
data = []

# Load each PDF file
for pdf_path in pdf_paths:
    loader = PyPDFLoader(pdf_path)
    data.extend(loader.load())

print(f"Total number of pages loaded: {len(data)}")

# Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
docs = text_splitter.split_documents(data)
print(f"Total number of chunks: {len(docs)}")

# Initialize embeddings
embeddings = HuggingFaceEmbeddings()

# Create vector store
vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)

# Create retriever
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

# Initialize the language model
model_id = "tiiuae/falcon-7b"
text_generation_pipeline = pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    max_new_tokens=400,
    device=0
)

llm = HuggingFacePipeline(pipeline=text_generation_pipeline)

# Define prompt template
prompt_template = """
<|system|>
Answer the question based on your knowledge. Use the following context to help:

{context}

</s>
<|user|>
{question}
</s>
<|assistant|>
"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=prompt_template,
)

# Create chain
llm_chain = prompt | llm | StrOutputParser()
rag_chain = {"context": retriever, "question": RunnablePassthrough()} | llm_chain

# Example usage
question = "What is discussed in these documents?"
response = rag_chain.invoke(question)
print(response)