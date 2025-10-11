"""Deprecated module.

This file previously contained the 'old' loader implementation. The project
now consolidates the loader into `document_loader.py`. Importing this module
will raise an ImportError instructing developers to use the canonical file.
"""

raise ImportError("The module 'document_loader_old' is deprecated. Use 'document_loader' instead.")
from rag_kmk.vector_db.database import ChromaDBStatus  # Add this import


