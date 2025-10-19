"""vector_db package for rag_kmk.

Keep top-level import minimal to avoid loading chromadb (heavy) on import.
"""

from .database import summarize_collection

# Re-export query helpers so `from rag_kmk.vector_db import retrieve_chunks` works.
# Import inside try/except to avoid import-time crashes when query has issues.
try:
    from .query import retrieve_chunks, show_results  # type: ignore
except Exception:
    retrieve_chunks = None
    show_results = None

# Do not expose anything publicly
# If you want to allow internal imports, you can do:
# from . import database
__all__ = []