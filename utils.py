# utils.py

import os
from dotenv import load_dotenv
from llama_index import (
    ServiceContext,
    VectorStoreIndex,
    LLMPredictor,
    PromptHelper,
    SimpleDirectoryReader,
    StorageContext
)
from langchain_openai import ChatOpenAI
from llama_index.vector_stores import PineconeVectorStore
from typing import Optional
import logging
from llama_index.readers import download_loader
from pinecone import (ServerlessSpec, Pinecone)
import time
import asyncio
load_dotenv()

class PineconeRAGManager:
    def __init__(self):
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "rag-chatbot")
        
        try:
            # Try to get the existing index first
            self.pinecone_index = self.pc.Index(self.index_name)
        except Exception as e:
            # If index doesn't exist, create it
            if self.index_name not in self.pc.list_indexes():
                try:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=1536,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud="aws",
                            region="us-east-1"
                        ),
                        deletion_protection="disabled"
                    )
                    # Wait for index to be ready
                    while not self.pc.describe_index(self.index_name).status['ready']:
                        time.sleep(1)
                    
                    self.pinecone_index = self.pc.Index(self.index_name)
                except Exception as create_error:
                    self.logger.error(f"Failed to create index: {str(create_error)}")
                    raise
        
        # Initialize LLM
        self.llm_predictor = LLMPredictor(
            llm=ChatOpenAI(
                temperature=0,
                model_name="gpt-4",
                api_key=os.getenv("OPENAI_API_KEY")
            )
        )
        
        # Set up service context with more aggressive chunking
        self.service_context = ServiceContext.from_defaults(
            llm_predictor=self.llm_predictor,
            chunk_size=256,
            chunk_overlap=50
        )

    def get_namespace(self, chat_id: int) -> str:
        return f"chat_{chat_id}"

    def get_vector_store(self, chat_id: int) -> PineconeVectorStore:
        return PineconeVectorStore(
            pinecone_index=self.pinecone_index,
            namespace=self.get_namespace(chat_id)
        )

    def get_index(self, chat_id: int) -> Optional[VectorStoreIndex]:
        try:
            vector_store = self.get_vector_store(chat_id)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            return VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
                service_context=self.service_context
            )
        except Exception as e:
            self.logger.error(f"Error getting index for chat {chat_id}: {str(e)}")
            return None

    async def ingest_document(self, file_path: str, chat_id: int):
        try:
            # Load documents based on file type
            if file_path.lower().endswith('.txt'):
                # Special handling for text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Create a Document object
                from llama_index.schema import Document
                document = Document(text=text)
                
                # Create documents with text splitter
                from llama_index.node_parser import SimpleNodeParser
                
                parser = SimpleNodeParser.from_defaults(
                    chunk_size=256,
                    chunk_overlap=50,
                    include_metadata=True,
                    include_prev_next_rel=True
                )
                
                nodes = parser.get_nodes_from_documents([document])
                
                # Create vector store with chat-specific namespace
                vector_store = self.get_vector_store(chat_id)
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # Create and store the index
                index = VectorStoreIndex(
                    nodes,
                    storage_context=storage_context,
                    service_context=self.service_context
                )
                
            else:
                # Original handling for PDF and DOCX files
                if file_path.lower().endswith('.pdf'):
                    PDFReader = download_loader("PDFReader")
                    loader = PDFReader()
                    documents = loader.load_data(file=file_path)
                elif file_path.lower().endswith('.docx'):
                    DocxReader = download_loader("DocxReader")
                    loader = DocxReader()
                    documents = loader.load_data(file=file_path)
                else:
                    loader = SimpleDirectoryReader(input_files=[file_path])
                    documents = loader.load_data()

                vector_store = self.get_vector_store(chat_id)
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    service_context=self.service_context
                )

            self.logger.info(f"Successfully ingested document for chat {chat_id}")
            
            # Add 5 second delay after ingestion
            await asyncio.sleep(5)
            
            return index

        except Exception as e:
            self.logger.error(f"Error ingesting document for chat {chat_id}: {str(e)}")
            raise

    async def generate_response(self, query: str, chat_id: int) -> str:
        try:
            index = self.get_index(chat_id)
            if not index:
                return "No knowledge base found. Please upload some documents first."

            # Log the query
            self.logger.info(f"Query for chat {chat_id}: {query}")

            query_engine = index.as_query_engine(
                similarity_top_k=3,
                streaming=True
            )
            
            response = query_engine.query(query)
            
            # Log the retrieved chunks
            if hasattr(response, 'source_nodes'):
                if not response.source_nodes:  # Check if there are any retrieved chunks
                    return "No relevant information found in the knowledge base."
                    
                self.logger.info(f"Retrieved chunks for chat {chat_id}:")
                for idx, node in enumerate(response.source_nodes):
                    self.logger.info(f"Chunk {idx + 1}:")
                    self.logger.info(f"Score: {node.score}")
                    self.logger.info(f"Content: {node.node.text}")
                    self.logger.info("---")
            
            response_text = str(response)
            if not response_text.strip():  # Check if response is empty or just whitespace
                return "I couldn't generate a meaningful response from the available information."
            
            return response_text

        except Exception as e:
            self.logger.error(f"Error generating response for chat {chat_id}: {str(e)}")
            return f"An error occurred while generating the response: {str(e)}"

