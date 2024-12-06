# utils.py

import os
from dotenv import load_dotenv
from llama_index import (
    ServiceContext,
    VectorStoreIndex,
    LLMPredictor,
    PromptHelper,
    SimpleDirectoryReader
)
from langchain_openai import ChatOpenAI

load_dotenv()

def ingest_document(file_path: str):
    # Use SimpleDirectoryReader to read the document
    from llama_index import download_loader

    # For PDF files
    if file_path.lower().endswith('.pdf'):
        PDFReader = download_loader("PDFReader")
        loader = PDFReader()
        documents = loader.load_data(file=file_path)
    # For Word documents
    elif file_path.lower().endswith('.docx'):
        DocxReader = download_loader("DocxReader")
        loader = DocxReader()
        documents = loader.load_data(file=file_path)
    # For text files
    else:
        loader = SimpleDirectoryReader(input_files=[file_path])
        documents = loader.load_data()

    # Initialize LLM and prompt helper
    llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=0, model_name="gpt-4"))
    max_input_size = 4096
    num_output = 512
    max_chunk_overlap = 0.5
    chunk_size_limit = 600

    prompt_helper = PromptHelper(max_input_size, num_output, max_chunk_overlap, chunk_size_limit=chunk_size_limit)

    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper)

    # Build the index
    index = VectorStoreIndex.from_documents(documents, service_context=service_context)

    return index

def generate_response(user_input: str, index) -> str:
    # Create a query engine
    query_engine = index.as_query_engine()

    # Get the response from the LLM
    response = query_engine.query(user_input)

    return str(response)

