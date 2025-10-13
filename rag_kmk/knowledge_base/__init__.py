from .document_loader import build_knowledge_base, load_and_add_documents

"""Knowledge-base package exports.

This package exposes a single `build_knowledge_base` function located in
`document_loader.py`. Historically there was a docling-based loader, but the
project now uses the consolidated `document_loader.py` implementation.
"""

__all__ = ['build_knowledge_base', 'load_and_add_documents']