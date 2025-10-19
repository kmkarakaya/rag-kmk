"""Configuration module for rag-kmk.

This module provides access to the application configuration, including
vector database settings, LLM settings, and other application-wide
parameters.
"""

# Expose the config module for internal imports (do not import rag_kmk here)
from . import config

__all__ = ["config"]