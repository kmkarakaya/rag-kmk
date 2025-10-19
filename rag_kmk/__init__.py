"""Top-level package for rag-kmk.

Avoid importing heavy or application-specific modules at import time.
Provide a lazy factory for rag_client to prevent import-time side effects.
"""

__author__ = "Murat Karakaya"
__email__ = "kmkarakaya@gmail.com"
__version__ = "0.0.55"

from .config.config import CONFIG


def rag_client(*args, **kwargs):
    """Lazy factory that returns an instance of the rag_client.

    Call as: from rag_kmk import rag_client
             rag = rag_client(...)  # this imports the real class lazily
    """
    # Import here to avoid import-time side effects and circular imports
    from .rag_client import rag_client as _RagClient

    return _RagClient(*args, **kwargs)

__all__ = ["CONFIG", "rag_client"]
