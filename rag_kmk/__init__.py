"""Top-level package for rag-kmk."""

__author__ = """Murat Karakaya"""
__email__ = "kmkarakaya@gmail.com"
__version__ = "0.0.49"


from .config.config import load_config
import os
import yaml

# Define the initialize_rag function
def initialize_rag(custom_config_path=None):
    """
        This module initialization ensures that rag-kmk is properly set up upon import.
        Initialize the RAG system with either the default or a custom config.
    """
    CONFIG = load_config() # Load default config first
    print(f"********* 🔔 Loading default config *********")

    if custom_config_path and os.path.exists(custom_config_path):
        try:
            with open(custom_config_path, 'r') as f:
                yaml.safe_load(f)  # Validate YAML
            print(f"********* 🔔 Loading custom config from: {custom_config_path} *********")
            CONFIG = load_config(custom_config_path)
        except (yaml.YAMLError, FileNotFoundError, Exception) as e:
            print(f"*********🚩 Error loading config from {custom_config_path}: {e}. Using default config.")

    return CONFIG

# Load a safe default configuration quietly so modules that reference CONFIG at import
# time do not fail. This avoids network or interactive side-effects while keeping
# import-time configuration available. Call `initialize_rag()` explicitly to
# override or re-load configuration at runtime if needed.
try:
    CONFIG = load_config() or {}
except Exception:
    CONFIG = {}


__all__ = ['build_knowledge_base', 'build_vector_db', 'build_rag_llm', 'initialize_rag', 'CONFIG']
