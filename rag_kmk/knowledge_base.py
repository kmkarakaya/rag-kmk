"""
Knowledge base construction and document loading.

This module acts as the public API for the knowledge_base package,
re-exporting the main `build_knowledge_base` function from the
internal `document_loader` module.
"""

from .document_loader import build_knowledge_base, load_and_add_documents

__all__ = ['build_knowledge_base', 'load_and_add_documents']
