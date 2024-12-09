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
from notion_loader import NotionDatabaseLoader
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

        self.notion_namespace = "notion_content"  # Single namespace for all Notion data

    def get_namespace(self, chat_id: int) -> str:
        return f"chat_{chat_id}"

    def get_vector_store(self) -> PineconeVectorStore:
        return PineconeVectorStore(
            pinecone_index=self.pinecone_index,
            namespace=self.notion_namespace
        )

    def get_index(self, chat_id: int) -> Optional[VectorStoreIndex]:
        try:
            vector_store = self.get_vector_store()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            return VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
                service_context=self.service_context,
                use_async=True  # Add async support
            )
        except Exception as e:
            self.logger.error(f"Error getting index for chat {chat_id}: {str(e)}")
            return None

    async def ingest_document(self, file_path: str, chat_id: int):
        try:
            start_time = time.perf_counter()
            
            # Load documents based on file type
            if file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                from llama_index.schema import Document
                document = Document(text=text)
                
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
                
                # Create index synchronously since we're in an async context
                index = VectorStoreIndex.from_documents(
                    [document],
                    storage_context=storage_context,
                    service_context=self.service_context,
                    show_progress=True
                )
                
            else:
                # Handle other file types
                if file_path.lower().endswith('.pdf'):
                    PDFReader = download_loader("PDFReader")
                    loader = PDFReader()
                    documents = loader.load_data(file=file_path)
                elif file_path.lower().endswith('.docx'):
                    DocxReader = download_loader("DocxReader")
                    loader = DocxReader()
                    documents = loader.load_data(file=file_path)
                else:
                    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

                vector_store = self.get_vector_store()
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # Create index synchronously
                index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    service_context=self.service_context,
                    show_progress=True
                )

            duration = time.perf_counter() - start_time
            self.logger.info(f"Index creation took {duration:.2f} seconds for chat {chat_id}")
            
            remaining_time = max(5 - duration, 0)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
                
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

    async def ingest_notion_database(self, chat_id: int):
        try:
            start_time = time.perf_counter()
            
            # Load documents from Notion
            notion_loader = NotionDatabaseLoader()
            documents = await notion_loader.load_documents()
            
            # Create vector store and index using notion_namespace
            vector_store = self.get_vector_store()  # This now uses notion_namespace
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            index = VectorStoreIndex(
                documents,
                storage_context=storage_context,
                service_context=self.service_context,
                # use_async=True
            )

            duration = time.perf_counter() - start_time
            self.logger.info(f"Notion database ingestion took {duration:.2f} seconds for chat {chat_id}")
            
            remaining_time = max(5 - duration, 0)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
                
            return index

        except Exception as e:
            self.logger.error(f"Error ingesting Notion database for chat {chat_id}: {str(e)}")
            raise

    async def update_notion_page(self, page_id: str):
        try:
            namespace = f"notion_page_{page_id}"
            logging.info(f"🔄 Updating/creating namespace: {namespace}")
            
            # Load updated page content
            notion_loader = NotionDatabaseLoader()
            updated_document = await notion_loader.load_page(page_id)
            
            # Create new vectors in page-specific namespace
            vector_store = PineconeVectorStore(
                pinecone_index=self.pinecone_index,
                namespace=namespace
            )
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Create index synchronously to avoid event loop issues
            index = VectorStoreIndex.from_documents(
                [updated_document],
                storage_context=storage_context,
                service_context=self.service_context,
                # show_progress=True
            )
            
            self.logger.info(f"✅ Updated vectors for Notion page {page_id} in namespace {namespace}")
            return index
            
        except Exception as e:
            self.logger.error(f"❌ Error updating Notion content: {str(e)}")
            raise

