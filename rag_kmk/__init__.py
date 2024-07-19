"""Top-level package for rag-kmk."""

__author__ = """Murat Karakaya"""
__email__ = "kmkarakaya@gmail.com"
__version__ = "0.0.19"


from .utils.config import load_config
#from .knowledge_base import build_knowledge_base
#from .vector_db import build_vector_db
#from .chat_flow import build_rag_llm

# Define the initialize_rag function
def initialize_rag(custom_config_path=None):
    """
        This module initialization ensures that rag-kmk is properly set up upon import.
        Initialize the RAG system with either the default or a custom config.
    """
    if custom_config_path:
        CONFIG= load_config(custom_config_path)
        return CONFIG
    else:
        CONFIG= load_config()
        return CONFIG

# Load the configuration when the module is imported
try:
    CONFIG = initialize_rag()
    print(f"RAG-KMK initialized with config")
except Exception as e:
    print(f"Error initializing rag-kmk module: {e}")



__all__ = ['build_knowledge_base', 'build_vector_db', 'build_rag_llm', 'initialize_rag', 'CONFIG']