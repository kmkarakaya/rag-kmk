import os
from rag_kmk import CONFIG
from rag_kmk.knowledge_base.text_splitter import convert_Pages_ChunkinChar, convert_Chunk_Token, add_meta_data, add_document_to_collection
from rag_kmk.vector_db import create_chroma_client
from rag_kmk.vector_db.database import ChromaDBStatus  # Add this import
from docling.document_converter import DocumentConverter
"""Deprecated docling-based loader.

Docling integration has been removed from the project's default build.
This placeholder raises an ImportError to avoid accidental imports of the
docling SDK. If you intentionally want the old docling implementation,
restore it from your VCS history.
"""

raise ImportError("The module 'document_loader_docling' is deprecated and no longer available. Use 'document_loader.py'.")

