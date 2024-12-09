from notion_client import Client
from llama_index.readers.schema.base import Document
from typing import List
import os
from datetime import datetime
import logging

class NotionDatabaseLoader:
    def __init__(self):
        self.notion = Client(auth=os.getenv("NOTION_API_KEY"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")

    async def load_documents(self) -> List[Document]:
        pages = self.notion.databases.query(database_id=self.database_id).get("results")
        documents = []

        for page in pages:
            # Get page content
            page_id = page["id"]
            page_content = self.notion.blocks.children.list(block_id=page_id)
            
            # Extract text content from blocks
            text_content = self._extract_text_from_blocks(page_content["results"])
            
            # Create metadata
            metadata = {
                "source": f"notion_page_{page_id}",
                "created_time": page.get("created_time"),
                "title": self._get_page_title(page),
            }
            
            # Create document
            doc = Document(
                text=text_content,
                metadata=metadata
            )
            documents.append(doc)

        return documents

    def _extract_text_from_blocks(self, blocks):
        text_content = []
        
        for block in blocks:
            block_type = block["type"]
            if block_type == "paragraph":
                text = block["paragraph"]["rich_text"]
                if text:
                    text_content.append(self._get_text_from_rich_text(text))
            elif block_type == "heading_1":
                text = block["heading_1"]["rich_text"]
                if text:
                    text_content.append(f"# {self._get_text_from_rich_text(text)}")
            elif block_type == "heading_2":
                text = block["heading_2"]["rich_text"]
                if text:
                    text_content.append(f"## {self._get_text_from_rich_text(text)}")
            elif block_type == "heading_3":
                text = block["heading_3"]["rich_text"]
                if text:
                    text_content.append(f"### {self._get_text_from_rich_text(text)}")

        return "\n\n".join(text_content)

    def _get_text_from_rich_text(self, rich_text):
        return " ".join([text["plain_text"] for text in rich_text])

    def _get_page_title(self, page):
        if "properties" in page and "title" in page["properties"]:
            title = page["properties"]["title"]
            if "title" in title and title["title"]:
                return self._get_text_from_rich_text(title["title"])
        return "Untitled"

    async def load_page(self, page_id: str) -> Document:
        try:
            # Get page content
            page = self.notion.pages.retrieve(page_id=page_id)
            page_content = self.notion.blocks.children.list(block_id=page_id)
            
            # Extract text content from blocks
            text_content = self._extract_text_from_blocks(page_content["results"])
            
            # Create metadata
            metadata = {
                "source": f"notion_page_{page_id}",
                "created_time": page.get("created_time"),
                "title": self._get_page_title(page),
                "page_id": page_id
            }
            
            # Create document
            doc = Document(
                text=text_content,
                metadata=metadata
            )
            
            return doc
            
        except Exception as e:
            logging.error(f"Error loading Notion page {page_id}: {str(e)}")
            raise
