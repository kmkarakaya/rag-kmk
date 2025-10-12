from .database import create_chroma_client, summarize_collection

# Re-export query helpers so `from rag_kmk.vector_db import retrieve_chunks` works.
# Import inside try/except to avoid import-time crashes when query has issues.
try:
    from .query import retrieve_chunks, show_results  # type: ignore
except Exception:
    retrieve_chunks = None
    show_results = None


__all__ = ['create_chroma_client', 'summarize_collection', 'retrieve_chunks', 'show_results']